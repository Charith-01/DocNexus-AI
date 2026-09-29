"""Password hashing and JWT helpers."""

from datetime import UTC, datetime, timedelta

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import settings


password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Hash a password with Argon2."""

    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its stored hash."""

    return password_hash.verify(password, hashed_password)


def create_access_token(subject: str) -> str:
    """Create a signed, expiring access token."""

    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> str | None:
    """Validate a token and return its subject."""

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY.get_secret_value(),
            algorithms=[settings.JWT_ALGORITHM],
        )
    except InvalidTokenError:
        return None

    subject = payload.get("sub")
    return subject if isinstance(subject, str) else None
