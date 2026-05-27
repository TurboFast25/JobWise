from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from pydantic import BaseModel
from src.database import get_db

router = APIRouter(tags=["cookbook"])


class CookbookRequest(BaseModel):
    recipe_id: int


@router.post(
    "/cookbook",
    status_code=201,
    tags=["cookbook"],
    responses={
        404: {"description": "User or recipe not found"},
        409: {"description": "Recipe already in cookbook"},
    },
)
def add_to_cookbook(
    body: CookbookRequest,
    user_id: int = Header(..., alias="user-id"),
    db: Session = Depends(get_db),
):
    if not db.execute(text("SELECT 1 FROM users WHERE user_id = :id"), {"id": user_id}).fetchone():
        raise HTTPException(404, "User not found")

    if not db.execute(text("SELECT 1 FROM recipes WHERE recipe_id = :id"), {"id": body.recipe_id}).fetchone():
        raise HTTPException(404, "Recipe not found")

    if db.execute(
        text("SELECT 1 FROM cookbook_entries WHERE user_id = :uid AND recipe_id = :rid"),
        {"uid": user_id, "rid": body.recipe_id}
    ).fetchone():
        raise HTTPException(409, "Already in your cookbook")

    # Atomic INSERT...SELECT: COUNT(*) and the INSERT happen in one statement,
    # so no concurrent transaction can slip in between the read and the write
    # and claim the same personal_rank value.
    db.execute(
        text("""
            INSERT INTO cookbook_entries (user_id, recipe_id, personal_rank)
            SELECT :uid, :rid, COUNT(*) + 1
            FROM cookbook_entries
            WHERE user_id = :uid
        """),
        {"uid": user_id, "rid": body.recipe_id}
    )
    db.commit()
    return {"status": "saved"}


@router.get(
    "/cookbook",
    status_code=200,
    tags=["cookbook"],
)
def get_cookbook(
    user_id: int = Header(..., alias="user-id"),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        text("""
            SELECT ce.recipe_id, ce.personal_rank, COALESCE(rev.z_score, 0.0) AS z_score
            FROM cookbook_entries ce
            LEFT JOIN reviews rev ON rev.recipe_id = ce.recipe_id AND rev.user_id = :uid
            WHERE ce.user_id = :uid
            ORDER BY ce.personal_rank
        """),
        {"uid": user_id}
    ).fetchall()

    return {
        "user_rankings": [
            {"recipe_id": r.recipe_id, "personal_rank": r.personal_rank, "z_score": round(r.z_score, 4)}
            for r in rows
        ]
    }
