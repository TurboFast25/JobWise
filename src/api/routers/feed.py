from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import Optional
from src.database import get_db
from src.api.sql_expressions import Z_SCORE_EXPR, USER_STATS_LATERAL

router = APIRouter(tags=["feed"])


@router.get(
    "/feed",
    status_code=200,
    tags=["feed"],
)
def get_feed(
    user_id: int = Header(..., alias="user-id"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    category: Optional[str] = None,
    db: Session = Depends(get_db),
):
    # Trust score = sum of z_scores for followed reviewers (trust_weight is always 1.0,
    # stored as a computed constant rather than a persisted column).
    # Secondary sort by total review count so that when trust scores are all 0 (new user
    # with no follows), more popular recipes still bubble up.
    category_clause = "AND LOWER(r.category) = LOWER(:category)" if category else ""
    params = {"uid": user_id, "limit": limit, "offset": offset}
    if category:
        params["category"] = category

    rows = db.execute(
        text(f"""
            SELECT
                r.recipe_id,
                r.title,
                r.category,
                r.is_canonical,
                COALESCE(SUM(CASE WHEN f.followee_id IS NOT NULL THEN ({Z_SCORE_EXPR}) END), 0) AS trust_score,
                COUNT(DISTINCT rev.review_id) AS review_count,
                array_agg(DISTINCT u.username) FILTER (WHERE f.follower_id = :uid AND u.username IS NOT NULL) AS trusted_reviewers
            FROM recipes r
            LEFT JOIN reviews rev ON rev.recipe_id = r.recipe_id
            {USER_STATS_LATERAL}
            LEFT JOIN follows f ON f.followee_id = rev.user_id AND f.follower_id = :uid
            LEFT JOIN users u ON u.user_id = rev.user_id
            WHERE r.is_canonical = true
              {category_clause}
            GROUP BY r.recipe_id, r.title, r.category, r.is_canonical
            ORDER BY trust_score DESC, review_count DESC
            LIMIT :limit OFFSET :offset
        """),
        params
    ).fetchall()

    return [
        {
            "recipe_id": r.recipe_id,
            "title": r.title,
            "category": r.category,
            "trust_score": round(r.trust_score, 4),
            "trusted_reviewers": r.trusted_reviewers or [],
            "is_canonical": r.is_canonical,
        }
        for r in rows
    ]
