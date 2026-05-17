import pytest
from datetime import datetime, timezone, timedelta
from jose import jwt

from app.core.jwt import decode_and_validate

TEST_SECRET = "change_me_super_secret"
TEST_ALG = "HS256"


def make_token(payload: dict) -> str:
    return jwt.encode(payload, TEST_SECRET, algorithm=TEST_ALG)


def test_decode_valid_token():
    now = datetime.now(timezone.utc)
    token = make_token({"sub": "42", "role": "user", "exp": now + timedelta(hours=1)})
    payload = decode_and_validate(token)
    assert payload["sub"] == "42"


def test_decode_garbage_token():
    with pytest.raises(ValueError):
        decode_and_validate("garbage")


def test_decode_expired_token():
    now = datetime.now(timezone.utc)
    token = make_token({"sub": "42", "role": "user", "exp": now - timedelta(seconds=1)})
    with pytest.raises(ValueError, match="expired"):
        decode_and_validate(token)
