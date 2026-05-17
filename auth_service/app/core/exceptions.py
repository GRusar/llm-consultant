from fastapi import HTTPException


class BaseHTTPException(HTTPException):
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)


class UserAlreadyExistsError(BaseHTTPException):
    def __init__(self) -> None:
        super().__init__(409, "User with this email already exists")


class InvalidCredentialsError(BaseHTTPException):
    def __init__(self) -> None:
        super().__init__(401, "Invalid email or password")


class InvalidTokenError(BaseHTTPException):
    def __init__(self) -> None:
        super().__init__(401, "Invalid or malformed token")


class TokenExpiredError(BaseHTTPException):
    def __init__(self) -> None:
        super().__init__(401, "Token has expired")


class UserNotFoundError(BaseHTTPException):
    def __init__(self) -> None:
        super().__init__(404, "User not found")


class PermissionDeniedError(BaseHTTPException):
    def __init__(self) -> None:
        super().__init__(403, "Permission denied")
