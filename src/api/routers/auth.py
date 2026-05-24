from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.api.auth import create_access_token, hash_password, verify_password
from src.api.db_helpers import atomic
from src.api.schemas import CreateUserRequest, LoginRequest, TokenResponse, UserResponse
from src.database import get_db

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.execute(
        text("SELECT user_id, username, password_hash FROM users WHERE username = :u"),
        {"u": body.username},
    ).fetchone()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    return TokenResponse(access_token=create_access_token(user.user_id, user.username))


@router.post("/users", status_code=201, response_model=UserResponse)
def create_user(body: CreateUserRequest, db: Session = Depends(get_db)) -> UserResponse:
    password_hash = hash_password(body.password)

    with atomic(db):
        user = db.execute(
            text(
                """
                INSERT INTO users (username, email, trust_authority, password_hash)
                VALUES (:username, :email, 0.0, :password_hash)
                RETURNING user_id, username, trust_authority
                """
            ),
            {
                "username": body.username,
                "email": body.email,
                "password_hash": password_hash,
            },
        ).fetchone()

    if user is None:
        raise HTTPException(status_code=500, detail="Failed to create user")

    return UserResponse(
        user_id=user.user_id,
        username=user.username,
        trust_authority=round(user.trust_authority, 4),
    )
