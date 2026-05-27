from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.api.db_helpers import atomic
from src.api.deps import get_current_user_id, get_optional_user_id
from src.api.ingredient_helpers import link_recipe_ingredients
from src.api.schemas import (
    IngestRequest,
    IngestResponse,
    IngredientItem,
    RecipeDetailResponse,
    TrustBreakdownResponse,
    TrustedContribution,
)
from src.api.sql_expressions import TRUST_WEIGHT_EXPR, USER_STATS_LATERAL, Z_SCORE_EXPR
from src.database import get_db

router = APIRouter(tags=["recipes"])

DUPLICATE_MESSAGE = "A similar recipe already exists; no new entry was created."
JACCARD_THRESHOLD = 0.5

RECIPE_DETAIL_QUERY = """
    SELECT
        r.recipe_id,
        r.title,
        r.instructions,
        r.is_canonical,
        r.category,
        r.author_id,
        COALESCE(
            array_agg(c.name ORDER BY c.ingredient_id)
            FILTER (WHERE c.ingredient_id IS NOT NULL),
            ARRAY[]::varchar[]
        ) AS ingredient_names,
        COALESCE(
            array_agg(ri.quantity ORDER BY c.ingredient_id)
            FILTER (WHERE c.ingredient_id IS NOT NULL),
            ARRAY[]::varchar[]
        ) AS ingredient_quantities
    FROM recipes r
    LEFT JOIN recipe_ingredients ri ON ri.recipe_id = r.recipe_id
    LEFT JOIN ingredient_catalog c ON c.ingredient_id = ri.ingredient_id
    WHERE r.recipe_id = :id
    GROUP BY r.recipe_id, r.title, r.instructions, r.is_canonical, r.category, r.author_id
"""

CANDIDATE_RECIPES_QUERY = """
    SELECT r.recipe_id, array_agg(c.name) AS ingredients
    FROM recipes r
    JOIN recipe_ingredients ri ON ri.recipe_id = r.recipe_id
    JOIN ingredient_catalog c ON c.ingredient_id = ri.ingredient_id
    WHERE r.is_canonical = true
      AND r.recipe_id IN (
          SELECT DISTINCT ri2.recipe_id
          FROM recipe_ingredients ri2
          JOIN ingredient_catalog c2 ON c2.ingredient_id = ri2.ingredient_id
          WHERE lower(trim(c2.name)) = ANY(:incoming_names)
      )
    GROUP BY r.recipe_id
"""

TRUST_BREAKDOWN_QUERY = f"""
    SELECT
        r.recipe_id,
        r.title,
        COALESCE(SUM({TRUST_WEIGHT_EXPR} * ({Z_SCORE_EXPR})), 0) AS trust_score,
        COUNT(DISTINCT rev.review_id) AS review_count,
        AVG(rev.raw_score) AS global_average_raw_score
    FROM recipes r
    LEFT JOIN reviews rev ON rev.recipe_id = r.recipe_id
    {USER_STATS_LATERAL}
    LEFT JOIN follows f ON f.followee_id = rev.user_id AND f.follower_id = :uid
    WHERE r.recipe_id = :rid
    GROUP BY r.recipe_id, r.title
"""

TRUSTED_CONTRIBUTIONS_QUERY = f"""
    SELECT
        u.username,
        rev.raw_score,
        ({Z_SCORE_EXPR}) AS z_score,
        {TRUST_WEIGHT_EXPR} AS trust_weight,
        {TRUST_WEIGHT_EXPR} * ({Z_SCORE_EXPR}) AS weighted_contribution
    FROM reviews rev
    {USER_STATS_LATERAL}
    JOIN follows f ON f.followee_id = rev.user_id AND f.follower_id = :uid
    JOIN users u ON u.user_id = rev.user_id
    WHERE rev.recipe_id = :rid
    ORDER BY weighted_contribution DESC, u.username
"""

NON_TRUSTED_REVIEW_COUNT_QUERY = """
    SELECT COUNT(*) AS cnt
    FROM reviews rev
    WHERE rev.recipe_id = :rid
      AND NOT EXISTS (
          SELECT 1
          FROM follows f
          WHERE f.follower_id = :uid AND f.followee_id = rev.user_id
      )
"""


def _normalize_ingredients(raw_ingredients: list[str]) -> set[str]:
    return {item.lower().strip() for item in raw_ingredients if item.strip()}


def _jaccard_score(incoming: set[str], existing: set[str]) -> float:
    union = incoming | existing
    if not union:
        return 0.0
    return len(incoming & existing) / len(union)


def _parse_instructions(raw_instructions: str | None) -> list[str]:
    if not raw_instructions:
        return []
    return [step.strip() for step in raw_instructions.split(".") if step.strip()]


def _build_ingredient_items(names: list, quantities: list) -> list[IngredientItem]:
    return [
        IngredientItem(name=name, quantity=quantity or None)
        for name, quantity in zip(names, quantities)
    ]


@router.get("/recipes/{recipe_id}", response_model=RecipeDetailResponse)
def get_recipe(recipe_id: int, db: Session = Depends(get_db)) -> RecipeDetailResponse:
    row = db.execute(text(RECIPE_DETAIL_QUERY), {"id": recipe_id}).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Recipe not found")

    return RecipeDetailResponse(
        recipe_id=row.recipe_id,
        title=row.title,
        category=row.category,
        author_id=row.author_id,
        ingredients=_build_ingredient_items(row.ingredient_names, row.ingredient_quantities),
        instructions=_parse_instructions(row.instructions),
        is_canonical=row.is_canonical,
    )


@router.get("/recipes/{recipe_id}/trust_breakdown", response_model=TrustBreakdownResponse)
def get_trust_breakdown(
    recipe_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> TrustBreakdownResponse:
    summary = db.execute(
        text(TRUST_BREAKDOWN_QUERY),
        {"uid": user_id, "rid": recipe_id},
    ).fetchone()

    if not summary:
        raise HTTPException(status_code=404, detail="Recipe not found")

    trusted_rows = db.execute(
        text(TRUSTED_CONTRIBUTIONS_QUERY),
        {"uid": user_id, "rid": recipe_id},
    ).fetchall()

    non_trusted = db.execute(
        text(NON_TRUSTED_REVIEW_COUNT_QUERY),
        {"uid": user_id, "rid": recipe_id},
    ).fetchone()

    return TrustBreakdownResponse(
        recipe_id=summary.recipe_id,
        title=summary.title,
        trust_score=round(summary.trust_score, 4),
        review_count=summary.review_count,
        global_average_raw_score=(
            round(summary.global_average_raw_score, 4)
            if summary.global_average_raw_score is not None
            else None
        ),
        trusted_contributions=[
            TrustedContribution(
                username=row.username,
                raw_score=round(row.raw_score, 4),
                z_score=round(row.z_score, 4),
                trust_weight=round(row.trust_weight, 4),
                weighted_contribution=round(row.weighted_contribution, 4),
            )
            for row in trusted_rows
        ],
        non_trusted_review_count=non_trusted.cnt if non_trusted else 0,
    )


@router.post("/recipes/ingest", response_model=IngestResponse)
def ingest_recipe(
    body: IngestRequest,
    user_id: int | None = Depends(get_optional_user_id),
    db: Session = Depends(get_db),
) -> IngestResponse:
    incoming = _normalize_ingredients(body.ingredients)

    candidate_rows = db.execute(
        text(CANDIDATE_RECIPES_QUERY),
        {"incoming_names": list(incoming)},
    ).fetchall()

    best_match: int | None = None
    best_score = 0.0

    for row in candidate_rows:
        existing = _normalize_ingredients(row.ingredients)
        score = _jaccard_score(incoming, existing)
        if score > best_score:
            best_score = score
            best_match = row.recipe_id

    if best_score >= JACCARD_THRESHOLD and best_match is not None:
        with atomic(db):
            db.execute(
                text(
                    """
                    INSERT INTO recipe_merges (canonical_recipe_id, source_recipe_id, confidence)
                    VALUES (:canonical_id, NULL, :confidence)
                    """
                ),
                {"canonical_id": best_match, "confidence": round(best_score, 3)},
            )
        return IngestResponse(
            status="duplicate_detected",
            canonical_id=best_match,
            confidence=round(best_score, 3),
            message=DUPLICATE_MESSAGE,
        )

    with atomic(db):
        new_recipe = db.execute(
            text(
                """
                INSERT INTO recipes (title, instructions, is_canonical, category, author_id)
                VALUES (:title, '', true, :category, :author_id)
                RETURNING recipe_id
                """
            ),
            {"title": body.title, "category": body.category, "author_id": user_id},
        ).fetchone()

        if new_recipe is None:
            raise HTTPException(status_code=500, detail="Failed to create recipe")

        link_recipe_ingredients(db, new_recipe.recipe_id, body.ingredients)

    return IngestResponse(
        status="created",
        canonical_id=new_recipe.recipe_id,
        confidence=1.0,
    )
