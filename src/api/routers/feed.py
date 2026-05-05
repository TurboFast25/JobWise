from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import Optional
from src.database import get_db

router = APIRouter(tags=["feed"])


@router.get("/feed")
def get_feed(
    user_id: int = Header(..., alias="user-id"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    category: Optional[str] = None,
    db: Session = Depends(get_db),
):
    # Trust score = sum of (trust_weight * z_score) for everyone you follow who reviewed the recipe
    rows = db.execute(
        text("""
            SELECT
                r.recipe_id,
                r.title,
                r.is_canonical,
                COALESCE(SUM(f.trust_weight * rev.z_score), 0) AS trust_score,
                array_agg(DISTINCT u.username) FILTER (WHERE f.follower_id = :uid AND u.username IS NOT NULL) AS trusted_reviewers
            FROM recipes r
            LEFT JOIN reviews rev ON rev.recipe_id = r.recipe_id
            LEFT JOIN follows f ON f.followee_id = rev.user_id AND f.follower_id = :uid
            LEFT JOIN users u ON u.user_id = rev.user_id
            WHERE r.is_canonical = true
            GROUP BY r.recipe_id, r.title, r.is_canonical
            ORDER BY trust_score DESC
            LIMIT :limit OFFSET :offset
        """),
        {"uid": user_id, "limit": limit, "offset": offset}
    ).fetchall()

    return [
        {
            "recipe_id": r.recipe_id,
            "title": r.title,
            "trust_score": round(r.trust_score, 4),
            "trusted_reviewers": r.trusted_reviewers or [],
            "is_canonical": r.is_canonical,
        }
        for r in rows
    ]
