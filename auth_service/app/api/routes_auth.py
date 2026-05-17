from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import get_auth_uc, get_current_user_id
from app.schemas.auth import RegisterRequest, TokenResponse
from app.schemas.user import UserPublic
from app.usecases.auth import AuthUseCase

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserPublic, status_code=201)
async def register(
    body: RegisterRequest,
    uc: AuthUseCase = Depends(get_auth_uc),
) -> UserPublic:
    return await uc.register(email=body.email, password=body.password)


@router.post("/login", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    uc: AuthUseCase = Depends(get_auth_uc),
) -> TokenResponse:
    return await uc.login(email=form.username, password=form.password)


@router.get("/me", response_model=UserPublic)
async def me(
    user_id: int = Depends(get_current_user_id),
    uc: AuthUseCase = Depends(get_auth_uc),
) -> UserPublic:
    return await uc.me(user_id)
