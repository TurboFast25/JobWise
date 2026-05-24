from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.api.db_helpers import atomic
from src.api.deps import get_current_user_id
from src.api.schemas import ReviewRequest, ReviewResponse
from src.database import get_db

router = APIRouter(tags=["reviews"])


@router.post("/reviews", response_model=ReviewResponse)
def submit_review(
    body: ReviewRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ReviewResponse:
    with atomic(db):
        db.execute(
            text("SELECT user_id FROM users WHERE user_id = :uid FOR UPDATE"),
            {"uid": user_id},
        )

        stats = db.execute(
            text(
                """
                SELECT AVG(raw_score) AS mean, STDDEV(raw_score) AS std, COUNT(*) AS cnt
                FROM reviews
                WHERE user_id = :uid
                """
            ),
            {"uid": user_id},
        ).fetchone()

        if stats.cnt == 0 or stats.std is None or stats.std == 0:
            z_score = 0.0
        else:
            z_score = (body.raw_score - stats.mean) / stats.std

        review = db.execute(
            text(
                """
                INSERT INTO reviews (user_id, recipe_id, raw_score, z_score, comment)
                VALUES (:uid, :rid, :raw, :z, :comment)
                RETURNING review_id, z_score
                """
            ),
            {
                "uid": user_id,
                "rid": body.recipe_id,
                "raw": body.raw_score,
                "z": z_score,
                "comment": body.comment,
            },
        ).fetchone()

        if review is None:
            raise HTTPException(status_code=500, detail="Failed to submit review")

        db.execute(
            text(
                """
                UPDATE users
                SET trust_authority = (
                    SELECT AVG(ABS(z_score)) FROM reviews WHERE user_id = :uid
                )
                WHERE user_id = :uid
                """
            ),
            {"uid": user_id},
        )

    return ReviewResponse(review_id=review.review_id, z_score=round(review.z_score, 4))
