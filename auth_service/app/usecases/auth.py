from app.core.exceptions import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.core.security import create_access_token, hash_password, verify_password
from app.repositories.users import UsersRepository
from app.schemas.auth import TokenResponse
from app.schemas.user import UserPublic


class AuthUseCase:
    def __init__(self, repo: UsersRepository) -> None:
        self._repo = repo

    async def register(self, email: str, password: str) -> UserPublic:
        if await self._repo.get_by_email(email) is not None:
            raise UserAlreadyExistsError()
        user = await self._repo.create(email=email, password_hash=hash_password(password))
        return UserPublic.model_validate(user)

    async def login(self, email: str, password: str) -> TokenResponse:
        user = await self._repo.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError()
        return TokenResponse(access_token=create_access_token(sub=str(user.id), role=user.role))

    async def me(self, user_id: int) -> UserPublic:
        user = await self._repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError()
        return UserPublic.model_validate(user)
