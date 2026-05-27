from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from sqlalchemy.exc import IntegrityError

from src.api.db_helpers import atomic, map_integrity_error
from src.api.deps import get_current_user_id
from src.api.schemas import FollowRequest, FollowResponse
from src.database import get_db

router = APIRouter(tags=["social"])


def _create_follow(
    follower_id: int,
    followee_id: int,
    db: Session,
) -> FollowResponse:
    if follower_id == followee_id:
        raise HTTPException(status_code=400, detail="You can't follow yourself")

    result = None
    try:
        with atomic(db):
            result = db.execute(
                text(
                    """
                    INSERT INTO follows (follower_id, followee_id)
                    SELECT :me, :them
                    WHERE EXISTS (SELECT 1 FROM users WHERE user_id = :me)
                      AND EXISTS (SELECT 1 FROM users WHERE user_id = :them)
                    RETURNING follow_id, follower_id, followee_id, created_at
                    """
                ),
                {"me": follower_id, "them": followee_id},
            ).fetchone()
    except IntegrityError as exc:
        raise map_integrity_error(exc) from exc

    if result is None:
        raise HTTPException(status_code=404, detail="User not found")

    return FollowResponse(
        follow_id=result.follow_id,
        follower_id=result.follower_id,
        followee_id=result.followee_id,
        created_at=result.created_at,
        trust_weight=1.0,
    )


@router.post("/social/follows", response_model=FollowResponse)
@router.post("/follows", response_model=FollowResponse)
def follow_user(
    body: FollowRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> FollowResponse:
    return _create_follow(user_id, body.followee_id, db)
