"""Tests for password and token security helpers."""

from app.auth.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hashing_and_verification() -> None:
    encoded = hash_password("correct horse battery staple")

    assert encoded != "correct horse battery staple"
    assert verify_password("correct horse battery staple", encoded)
    assert not verify_password("wrong password", encoded)


def test_jwt_creation_and_validation() -> None:
    subject = "507f1f77bcf86cd799439011"
    token = create_access_token(subject)

    assert decode_access_token(token) == subject
    assert decode_access_token(f"{token}tampered") is None
