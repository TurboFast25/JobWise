from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.api.deps import get_current_user_id
from src.api.schemas import FeedItemResponse
from src.api.sql_expressions import TRUST_WEIGHT_EXPR, USER_STATS_LATERAL, Z_SCORE_EXPR
from src.database import get_db

router = APIRouter(tags=["feed"])

FEED_QUERY = f"""
    SELECT
        r.recipe_id,
        r.title,
        r.category,
        r.is_canonical,
        COALESCE(SUM({TRUST_WEIGHT_EXPR} * ({Z_SCORE_EXPR})), 0) AS trust_score,
        COUNT(DISTINCT rev.review_id) AS review_count,
        array_agg(DISTINCT u.username) FILTER (
            WHERE f.follower_id = :uid AND u.username IS NOT NULL
        ) AS trusted_reviewers
    FROM recipes r
    LEFT JOIN reviews rev ON rev.recipe_id = r.recipe_id
    {USER_STATS_LATERAL}
    LEFT JOIN follows f ON f.followee_id = rev.user_id AND f.follower_id = :uid
    LEFT JOIN users u ON u.user_id = rev.user_id
    WHERE r.is_canonical = true
      AND (:category IS NULL OR LOWER(r.category) = LOWER(:category))
    GROUP BY r.recipe_id, r.title, r.category, r.is_canonical
    ORDER BY trust_score DESC, review_count DESC
    LIMIT :limit OFFSET :offset
"""


def _fetch_feed(
    user_id: int,
    limit: int,
    offset: int,
    category: Optional[str],
    db: Session,
) -> list[FeedItemResponse]:
    rows = db.execute(
        text(FEED_QUERY),
        {"uid": user_id, "limit": limit, "offset": offset, "category": category},
    ).fetchall()

    return [
        FeedItemResponse(
            recipe_id=row.recipe_id,
            title=row.title,
            category=row.category,
            trust_score=round(row.trust_score, 4),
            review_count=row.review_count,
            trusted_reviewers=row.trusted_reviewers or [],
            is_canonical=row.is_canonical,
        )
        for row in rows
    ]


@router.get("/feed", response_model=list[FeedItemResponse])
@router.get("/recipes/feed", response_model=list[FeedItemResponse])
def get_feed(
    user_id: int = Depends(get_current_user_id),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
) -> list[FeedItemResponse]:
    return _fetch_feed(user_id, limit, offset, category, db)
