from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.api.db_helpers import atomic
from src.api.deps import get_current_user_id
from src.api.schemas import ReviewBody, ReviewRequest, ReviewResponse
from src.database import get_db

router = APIRouter(tags=["reviews"])


def _compute_z_score(stats, raw_score: float) -> float:
    if stats.cnt == 0 or stats.std is None or stats.std == 0:
        return 0.0
    return (raw_score - stats.mean) / stats.std


def _submit_review_for_recipe(
    recipe_id: int,
    raw_score: float,
    comment: str | None,
    user_id: int,
    db: Session,
) -> ReviewResponse:
    if not db.execute(
        text("SELECT 1 FROM recipes WHERE recipe_id = :rid"),
        {"rid": recipe_id},
    ).fetchone():
        raise HTTPException(status_code=404, detail="Recipe not found")

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

        z_score = _compute_z_score(stats, raw_score)

        review = db.execute(
            text(
                """
                INSERT INTO reviews (user_id, recipe_id, raw_score, comment)
                VALUES (:uid, :rid, :raw, :comment)
                RETURNING review_id
                """
            ),
            {
                "uid": user_id,
                "rid": recipe_id,
                "raw": raw_score,
                "comment": comment,
            },
        ).fetchone()

        if review is None:
            raise HTTPException(status_code=500, detail="Failed to submit review")

    return ReviewResponse(review_id=review.review_id, z_score=round(z_score, 4))


@router.post("/reviews", response_model=ReviewResponse)
def submit_review(
    body: ReviewRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ReviewResponse:
    return _submit_review_for_recipe(body.recipe_id, body.raw_score, body.comment, user_id, db)


@router.post("/recipes/{recipe_id}/reviews", response_model=ReviewResponse)
def submit_recipe_review(
    recipe_id: int,
    body: ReviewBody,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ReviewResponse:
    return _submit_review_for_recipe(recipe_id, body.raw_score, body.comment, user_id, db)
