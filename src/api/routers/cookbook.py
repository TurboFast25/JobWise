from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.api.db_helpers import atomic
from src.api.deps import get_current_user_id
from src.api.schemas import (
    CookbookRankingItem,
    CookbookRankingUpdateItem,
    CookbookRankingsRequest,
    CookbookRequest,
    CookbookResponse,
    StatusResponse,
)
from src.api.sql_expressions import USER_STATS_LATERAL, Z_SCORE_EXPR
from src.database import get_db

router = APIRouter(tags=["cookbook"])

COOKBOOK_QUERY = f"""
    SELECT
        ce.recipe_id,
        ce.personal_rank,
        COALESCE(({Z_SCORE_EXPR}), 0.0) AS z_score
    FROM cookbook_entries ce
    LEFT JOIN reviews rev ON rev.recipe_id = ce.recipe_id AND rev.user_id = :uid
    {USER_STATS_LATERAL}
    WHERE ce.user_id = :uid
    ORDER BY ce.personal_rank
"""


def _validate_rankings(
    rankings: list[CookbookRankingUpdateItem],
    cookbook_recipe_ids: set[int],
) -> None:
    if len(rankings) != len(cookbook_recipe_ids):
        raise HTTPException(
            status_code=422,
            detail="Rankings must include every recipe in your cookbook exactly once",
        )

    request_recipe_ids = {item.recipe_id for item in rankings}
    if request_recipe_ids != cookbook_recipe_ids:
        unknown = request_recipe_ids - cookbook_recipe_ids
        if unknown:
            raise HTTPException(
                status_code=404,
                detail=f"Recipe(s) not in your cookbook: {sorted(unknown)}",
            )
        raise HTTPException(
            status_code=422,
            detail="Rankings must include every recipe in your cookbook exactly once",
        )

    ranks = [item.personal_rank for item in rankings]
    if len(ranks) != len(set(ranks)):
        raise HTTPException(
            status_code=409,
            detail="Duplicate rank detected — please assign a unique rank to each recipe",
        )

    expected = list(range(1, len(ranks) + 1))
    if sorted(ranks) != expected:
        raise HTTPException(
            status_code=422,
            detail=f"Ranks must be contiguous integers from 1 to {len(ranks)}",
        )


@router.post("/cookbook", response_model=StatusResponse)
def add_to_cookbook(
    body: CookbookRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> StatusResponse:
    with atomic(db):
        db.execute(
            text("SELECT user_id FROM users WHERE user_id = :uid FOR UPDATE"),
            {"uid": user_id},
        )
        db.execute(
            text(
                """
                INSERT INTO cookbook_entries (user_id, recipe_id, personal_rank)
                VALUES (
                    :uid,
                    :rid,
                    (
                        SELECT COALESCE(MAX(personal_rank), 0) + 1
                        FROM cookbook_entries
                        WHERE user_id = :uid
                    )
                )
                """
            ),
            {"uid": user_id, "rid": body.recipe_id},
        )

    return StatusResponse(status="saved")


@router.put("/cookbook/rankings", response_model=CookbookResponse)
def reorder_cookbook(
    body: CookbookRankingsRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> CookbookResponse:
    with atomic(db):
        db.execute(
            text("SELECT user_id FROM users WHERE user_id = :uid FOR UPDATE"),
            {"uid": user_id},
        )

        existing_rows = db.execute(
            text("SELECT recipe_id FROM cookbook_entries WHERE user_id = :uid"),
            {"uid": user_id},
        ).fetchall()

        cookbook_recipe_ids = {row.recipe_id for row in existing_rows}
        if not cookbook_recipe_ids:
            raise HTTPException(status_code=422, detail="Your cookbook is empty")

        _validate_rankings(body.rankings, cookbook_recipe_ids)

        for item in body.rankings:
            db.execute(
                text(
                    """
                    UPDATE cookbook_entries
                    SET personal_rank = :rank
                    WHERE user_id = :uid AND recipe_id = :rid
                    """
                ),
                {"uid": user_id, "rid": item.recipe_id, "rank": item.personal_rank},
            )

    return get_cookbook(user_id=user_id, db=db)


@router.get("/cookbook", response_model=CookbookResponse)
def get_cookbook(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> CookbookResponse:
    rows = db.execute(text(COOKBOOK_QUERY), {"uid": user_id}).fetchall()

    return CookbookResponse(
        user_rankings=[
            CookbookRankingItem(
                recipe_id=row.recipe_id,
                personal_rank=row.personal_rank,
                z_score=round(row.z_score, 4),
            )
            for row in rows
        ]
    )
