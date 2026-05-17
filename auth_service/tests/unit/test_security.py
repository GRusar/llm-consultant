import pytest
from jose import JWTError

from app.core.security import hash_password, verify_password, create_access_token, decode_access_token


def test_hash_password_not_equal_plain():
    hashed = hash_password("mysecretpassword")
    assert hashed != "mysecretpassword"


def test_verify_password_correct():
    hashed = hash_password("correctpassword")
    assert verify_password("correctpassword", hashed) is True


def test_verify_password_wrong():
    hashed = hash_password("correctpassword")
    assert verify_password("wrongpassword", hashed) is False


def test_create_and_decode_token():
    token = create_access_token(sub="42", role="user")
    payload = decode_access_token(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "user"
    assert "iat" in payload
    assert "exp" in payload


def test_decode_invalid_token():
    with pytest.raises(JWTError):
        decode_access_token("this.is.garbage")
