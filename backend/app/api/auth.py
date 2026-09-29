"""Authentication API routes."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.errors import DuplicateKeyError

from app.auth.dependencies import get_current_user
from app.auth.security import create_access_token, hash_password, verify_password
from app.db.mongodb import users_collection
from app.schemas.auth import TokenResponse, UserLogin, UserRegistration, UserResponse


router = APIRouter(prefix="/auth", tags=["Authentication"])


def _user_response(user: dict[str, Any]) -> UserResponse:
    return UserResponse(
        id=str(user["_id"]),
        email=user["email"],
        created_at=user["created_at"],
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(payload: UserRegistration) -> UserResponse:
    """Create a user with a normalized email and Argon2 password hash."""

    email = str(payload.email).strip().casefold()
    if users_collection.find_one({"email": email}, {"_id": 1}) is not None:
        raise HTTPException(status_code=409, detail="An account with this email exists")

    user = {
        "email": email,
        "password_hash": hash_password(payload.password),
        "created_at": datetime.now(UTC),
    }
    try:
        result = users_collection.insert_one(user)
    except DuplicateKeyError as exc:
        raise HTTPException(
            status_code=409, detail="An account with this email exists"
        ) from exc

    user["_id"] = result.inserted_id
    return _user_response(user)


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin) -> TokenResponse:
    """Authenticate without revealing which credential was incorrect."""

    email = str(payload.email).strip().casefold()
    user = users_collection.find_one({"email": email})
    if user is None or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(access_token=create_access_token(str(user["_id"])))


@router.get("/me", response_model=UserResponse)
def me(current_user: dict[str, Any] = Depends(get_current_user)) -> UserResponse:
    """Return the authenticated user's public profile."""

    return _user_response(current_user)
