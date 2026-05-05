from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from src.database import get_db

router = APIRouter(tags=["users"])


@router.get("/users/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.execute(
        text("SELECT user_id, username, trust_authority FROM users WHERE user_id = :id"),
        {"id": user_id}
    ).fetchone()

    if not user:
        raise HTTPException(404, "User not found")

    return {
        "user_id": user.user_id,
        "username": user.username,
        "trust_authority": round(user.trust_authority, 4),
    }
