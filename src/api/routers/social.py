from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.api.db_helpers import atomic
from src.api.deps import get_current_user_id
from src.api.schemas import FollowRequest, StatusResponse
from src.database import get_db

router = APIRouter(tags=["social"])


@router.post("/social/follows", response_model=StatusResponse)
def follow_user(
    body: FollowRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> StatusResponse:
    if user_id == body.followee_id:
        raise HTTPException(status_code=400, detail="You can't follow yourself")

    with atomic(db):
        result = db.execute(
            text(
                """
                INSERT INTO follows (follower_id, followee_id, trust_weight)
                SELECT :me, :them, 1.0
                WHERE EXISTS (SELECT 1 FROM users WHERE user_id = :me)
                  AND EXISTS (SELECT 1 FROM users WHERE user_id = :them)
                RETURNING follow_id
                """
            ),
            {"me": user_id, "them": body.followee_id},
        ).fetchone()

    if result is None:
        raise HTTPException(status_code=404, detail="User not found")

    return StatusResponse(status="following")
