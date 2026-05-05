from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
from src.database import get_db

router = APIRouter(tags=["reviews"])


class ReviewRequest(BaseModel):
    recipe_id: int
    raw_score: float = Field(..., ge=0.0, le=10.0)
    comment: Optional[str] = None


@router.post("/reviews")
def submit_review(body: ReviewRequest, user_id: int = Header(..., alias="user-id"), db: Session = Depends(get_db)):
    if not db.execute(text("SELECT 1 FROM users WHERE user_id = :id"), {"id": user_id}).fetchone():
        raise HTTPException(404, "User not found")

    if not db.execute(text("SELECT 1 FROM recipes WHERE recipe_id = :id"), {"id": body.recipe_id}).fetchone():
        raise HTTPException(404, "Recipe not found")

    if db.execute(
        text("SELECT 1 FROM reviews WHERE user_id = :uid AND recipe_id = :rid"),
        {"uid": user_id, "rid": body.recipe_id}
    ).fetchone():
        raise HTTPException(409, "You've already reviewed this recipe")

    # Z-score: normalize this rating against everything the user has rated before
    stats = db.execute(
        text("SELECT AVG(raw_score) AS mean, STDDEV(raw_score) AS std, COUNT(*) AS cnt FROM reviews WHERE user_id = :uid"),
        {"uid": user_id}
    ).fetchone()

    if stats.cnt == 0 or stats.std is None or stats.std == 0:
        z = 0.0
    else:
        z = (body.raw_score - stats.mean) / stats.std

    review = db.execute(
        text("""
            INSERT INTO reviews (user_id, recipe_id, raw_score, z_score, comment)
            VALUES (:uid, :rid, :raw, :z, :comment)
            RETURNING review_id, z_score
        """),
        {"uid": user_id, "rid": body.recipe_id, "raw": body.raw_score, "z": z, "comment": body.comment}
    ).fetchone()

    # Bump trust_authority based on how opinionated the user's ratings are
    db.execute(
        text("UPDATE users SET trust_authority = (SELECT AVG(ABS(z_score)) FROM reviews WHERE user_id = :uid) WHERE user_id = :uid"),
        {"uid": user_id}
    )

    db.commit()
    return {"review_id": review.review_id, "z_score": round(review.z_score, 4)}
