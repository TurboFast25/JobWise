from typing import Annotated

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.api.auth import decode_access_token
from src.database import get_db

bearer_scheme = HTTPBearer(auto_error=False)


def _resolve_user_id_from_header(user_id: int, db: Session) -> int:
    if not db.execute(text("SELECT 1 FROM users WHERE user_id = :id"), {"id": user_id}).fetchone():
        raise HTTPException(status_code=404, detail="User not found")
    return user_id


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    user_id_header: Annotated[int | None, Header(alias="user-id")] = None,
    db: Session = Depends(get_db),
) -> int:
    if credentials is not None and credentials.scheme.lower() == "bearer":
        try:
            payload = decode_access_token(credentials.credentials)
            user_id = int(payload["sub"])
        except (ValueError, KeyError, TypeError):
            raise HTTPException(status_code=401, detail="Invalid or expired token") from None

        if not db.execute(text("SELECT 1 FROM users WHERE user_id = :id"), {"id": user_id}).fetchone():
            raise HTTPException(status_code=401, detail="User no longer exists")
        return user_id

    if user_id_header is not None:
        return _resolve_user_id_from_header(user_id_header, db)

    raise HTTPException(status_code=401, detail="Missing or invalid authorization header")


def get_optional_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    user_id_header: Annotated[int | None, Header(alias="user-id")] = None,
    db: Session = Depends(get_db),
) -> int | None:
    if credentials is not None and credentials.scheme.lower() == "bearer":
        try:
            payload = decode_access_token(credentials.credentials)
            user_id = int(payload["sub"])
        except (ValueError, KeyError, TypeError):
            raise HTTPException(status_code=401, detail="Invalid or expired token") from None

        if not db.execute(text("SELECT 1 FROM users WHERE user_id = :id"), {"id": user_id}).fetchone():
            raise HTTPException(status_code=401, detail="User no longer exists")
        return user_id

    if user_id_header is not None:
        return _resolve_user_id_from_header(user_id_header, db)

    return None
