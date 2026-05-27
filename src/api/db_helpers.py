from collections.abc import Generator

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


def atomic(db: Session) -> Session:
    """Return a session context manager that commits on success and rolls back on failure."""
    return db.begin()


def map_integrity_error(error: IntegrityError) -> HTTPException:
    """Map Postgres integrity violations to meaningful HTTP errors."""
    orig = error.orig
    detail = str(orig)
    pgcode = getattr(orig, "pgcode", None)
    constraint = _constraint_name(error)

    if pgcode == "23505":
        if constraint in ("uq_cookbook_entry",):
            return HTTPException(status_code=409, detail="Already in your cookbook")
        if constraint == "uq_cookbook_user_rank":
            return HTTPException(
                status_code=409,
                detail="Duplicate rank detected — please assign a unique rank to each recipe",
            )
        if constraint == "uq_user_recipe_review":
            return HTTPException(status_code=409, detail="You've already reviewed this recipe")
        if constraint == "uq_follow":
            return HTTPException(status_code=409, detail="You're already following this user")
        if constraint == "users_username_key":
            return HTTPException(status_code=409, detail="Username is already taken")
        if constraint == "uq_user_email":
            return HTTPException(status_code=409, detail="Email is already registered")
        if "username" in detail:
            return HTTPException(status_code=409, detail="Username is already taken")
        if "email" in detail:
            return HTTPException(status_code=409, detail="Email is already registered")
        return HTTPException(status_code=409, detail="Resource already exists")

    if pgcode == "23503":
        if constraint and "cookbook_entries" in constraint:
            return HTTPException(status_code=404, detail="User or recipe not found")
        if constraint and "reviews" in constraint:
            return HTTPException(status_code=404, detail="User or recipe not found")
        if constraint and "follows" in constraint:
            return HTTPException(status_code=404, detail="User not found")
        if "cookbook_entries" in detail:
            return HTTPException(status_code=404, detail="User or recipe not found")
        if "reviews" in detail:
            return HTTPException(status_code=404, detail="User or recipe not found")
        if "follows" in detail:
            return HTTPException(status_code=404, detail="User not found")
        return HTTPException(status_code=404, detail="Referenced resource not found")

    return HTTPException(status_code=400, detail="Database constraint violation")


def _constraint_name(error: IntegrityError) -> str | None:
    orig = error.orig
    diag = getattr(orig, "diag", None)
    if diag is not None:
        name = getattr(diag, "constraint_name", None)
        if name:
            return name
    return None
