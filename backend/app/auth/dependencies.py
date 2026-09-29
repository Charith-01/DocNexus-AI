"""Reusable FastAPI authentication dependencies."""

from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.security import decode_access_token
from app.db.mongodb import users_collection


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    """Return the authenticated MongoDB user or reject the request."""

    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or credentials.scheme.casefold() != "bearer":
        raise credentials_error

    subject = decode_access_token(credentials.credentials)
    if subject is None:
        raise credentials_error

    try:
        user_id = ObjectId(subject)
    except InvalidId as exc:
        raise credentials_error from exc

    user = users_collection.find_one({"_id": user_id})
    if user is None:
        raise credentials_error
    return user
