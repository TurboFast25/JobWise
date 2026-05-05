from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from pydantic import BaseModel
from src.database import get_db

router = APIRouter(tags=["social"])


class FollowRequest(BaseModel):
    followee_id: int


@router.post("/social/follows")
def follow_user(body: FollowRequest, user_id: int = Header(..., alias="user-id"), db: Session = Depends(get_db)):
    if user_id == body.followee_id:
        raise HTTPException(400, "You can't follow yourself")

    if not db.execute(text("SELECT 1 FROM users WHERE user_id = :id"), {"id": user_id}).fetchone():
        raise HTTPException(404, "Your user account wasn't found")

    if not db.execute(text("SELECT 1 FROM users WHERE user_id = :id"), {"id": body.followee_id}).fetchone():
        raise HTTPException(404, "That user doesn't exist")

    if db.execute(
        text("SELECT 1 FROM follows WHERE follower_id = :me AND followee_id = :them"),
        {"me": user_id, "them": body.followee_id}
    ).fetchone():
        raise HTTPException(409, "You're already following this user")

    db.execute(
        text("INSERT INTO follows (follower_id, followee_id, trust_weight) VALUES (:me, :them, 1.0)"),
        {"me": user_id, "them": body.followee_id}
    )
    db.commit()
    return {"status": "following"}
