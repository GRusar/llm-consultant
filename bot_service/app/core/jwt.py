from jose import jwt, JWTError, ExpiredSignatureError
from app.core.config import settings


def decode_and_validate(token: str) -> dict:
    """Raises ValueError on any validation failure."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
    except ExpiredSignatureError:
        raise ValueError("Token has expired")
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}")
    if not payload.get("sub"):
        raise ValueError("Token missing sub claim")
    return payload
