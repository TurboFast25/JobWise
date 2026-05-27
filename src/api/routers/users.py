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


@router.post(
    "/users",
    status_code=201,
    tags=["users"],
    responses={
        409: {"description": "Username or email already exists"},
        422: {"description": "Invalid username"},
    },
)
def create_user(
    body: CreateUserRequest,
    db: Session = Depends(get_db),
):
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

@router.get(
    "/users/{user_id}/taste-profile",
    status_code=200,
    tags=["users"],
    responses={
        404: {"description": "User not found"},
    },
)
def get_taste_profile(
    user_id: int,
    db: Session = Depends(get_db),
):
    user = db.execute(
        text("SELECT user_id, username FROM users WHERE user_id = :id"),
        {"id": user_id},
    ).fetchone()

    if not user:
        raise HTTPException(404, "User not found")

    rows = db.execute(
        text("""
            SELECT
                r.recipe_id,
                r.title,
                COALESCE(r.category, 'Uncategorized') AS category,
                rev.raw_score,
                rev.z_score
            FROM reviews rev
            JOIN recipes r ON r.recipe_id = rev.recipe_id
            WHERE rev.user_id = :uid
        """),
        {"uid": user_id},
    ).fetchall()

    if not rows:
        return {
            "user_id": user.user_id,
            "username": user.username,
            "review_count": 0,
            "average_score": None,
            "favorite_category": None,
            "least_favorite_category": None,
            "category_breakdown": [],
            "most_positive_recipe": None,
            "most_negative_recipe": None,
        }

    category_stats = {}

    for row in rows:
        stats = category_stats.setdefault(
            row.category,
            {"category": row.category, "review_count": 0, "total_score": 0.0, "total_z_score": 0.0},
        )
        stats["review_count"] += 1
        stats["total_score"] += row.raw_score
        stats["total_z_score"] += row.z_score

    category_breakdown = []

    for stats in category_stats.values():
        category_breakdown.append({
            "category": stats["category"],
            "review_count": stats["review_count"],
            "average_score": round(stats["total_score"] / stats["review_count"], 4),
            "average_z_score": round(stats["total_z_score"] / stats["review_count"], 4),
        })

    category_breakdown.sort(key=lambda c: c["average_z_score"], reverse=True)

    most_positive = max(rows, key=lambda r: r.z_score)
    most_negative = min(rows, key=lambda r: r.z_score)

    return {
        "user_id": user.user_id,
        "username": user.username,
        "review_count": len(rows),
        "average_score": round(sum(r.raw_score for r in rows) / len(rows), 4),
        "favorite_category": category_breakdown[0]["category"],
        "least_favorite_category": category_breakdown[-1]["category"],
        "category_breakdown": category_breakdown,
        "most_positive_recipe": {
            "recipe_id": most_positive.recipe_id,
            "title": most_positive.title,
            "z_score": round(most_positive.z_score, 4),
        },
        "most_negative_recipe": {
            "recipe_id": most_negative.recipe_id,
            "title": most_negative.title,
            "z_score": round(most_negative.z_score, 4),
        },
    }

@router.get(
    "/users/{user_id}",
    status_code=200,
    tags=["users"],
    responses={
        404: {"description": "User not found"},
    },
)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
):
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
