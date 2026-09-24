import pytest
from datetime import timedelta
import jwt
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.config import settings


def test_password_hashing_and_verification():
    raw_password = "supersecretpassword123!"
    hashed = get_password_hash(raw_password)

    assert hashed != raw_password
    assert verify_password(raw_password, hashed) is True
    assert verify_password("wrongpassword", hashed) is False
    assert verify_password("", hashed) is False


def test_access_token_creation_and_decoding():
    user_id = "test-user-uuid-1234"
    token = create_access_token(subject=user_id)
    payload = decode_token(token)

    assert payload["sub"] == user_id
    assert payload["type"] == "access"
    assert "exp" in payload
    assert "iat" in payload


def test_refresh_token_creation_and_decoding():
    user_id = "test-user-uuid-5678"
    token = create_refresh_token(subject=user_id)
    payload = decode_token(token)

    assert payload["sub"] == user_id
    assert payload["type"] == "refresh"


def test_decode_invalid_token():
    with pytest.raises(jwt.InvalidTokenError):
        decode_token("this.is.not.a.valid.jwt.token")


def test_decode_expired_token():
    user_id = "expired-user"
    token = create_access_token(subject=user_id, expires_delta=timedelta(seconds=-10))
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(token)
