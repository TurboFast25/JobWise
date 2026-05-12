from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from src.database import get_db

router = APIRouter(tags=["users"])


class CreateUserRequest(BaseModel):
    username: str
    email: Optional[str] = None


@router.post("/users", status_code=201)
def create_user(body: CreateUserRequest, db: Session = Depends(get_db)):
    if not body.username.strip():
        raise HTTPException(422, "Username cannot be empty")

    if db.execute(text("SELECT 1 FROM users WHERE username = :u"), {"u": body.username}).fetchone():
        raise HTTPException(409, "Username is already taken")

    if body.email:
        if db.execute(text("SELECT 1 FROM users WHERE email = :e"), {"e": body.email}).fetchone():
            raise HTTPException(409, "Email is already registered")

    user = db.execute(
        text("INSERT INTO users (username, email, trust_authority) VALUES (:u, :e, 0.0) RETURNING user_id, username, trust_authority"),
        {"u": body.username.strip(), "e": body.email}
    ).fetchone()

    db.commit()
    return {"user_id": user.user_id, "username": user.username, "trust_authority": user.trust_authority}


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
