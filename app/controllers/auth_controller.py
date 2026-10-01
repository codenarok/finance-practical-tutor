"""Authentication controller handling registration and login flows."""
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy.orm import Session

from app.config import get_settings
from app.managers.user_manager import user_manager
from app.models.user import User
from app.services.database import get_db
from app.services.rate_limiter import limit_auth_attempts


settings = get_settings()
router = APIRouter(prefix="/api", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_BYTES = 72  # bcrypt ignores or rejects anything longer


class RegisterRequest(BaseModel):
    """Incoming payload for user registration."""

    email: EmailStr
    password: str = Field(..., min_length=MIN_PASSWORD_LENGTH)

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, value: str) -> str:
        if len(value.encode("utf-8")) > MAX_PASSWORD_BYTES:
            raise ValueError(f"Password must be at most {MAX_PASSWORD_BYTES} bytes")
        return value


class TokenResponse(BaseModel):
    """Response payload containing JWT token."""

    access_token: str
    token_type: str = "bearer"


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generate a signed JWT token."""

    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_db)) -> User:
    """Validate JWT token and retrieve the associated user."""

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError) as exc:  # token invalid, expired or malformed
        raise credentials_exception from exc
    user = user_manager.get_user_by_id(session, user_id)
    if user is None:
        raise credentials_exception
    return user


@router.post("/register", response_model=TokenResponse, dependencies=[Depends(limit_auth_attempts)])
def register_user(payload: RegisterRequest, session: Session = Depends(get_db)) -> TokenResponse:
    """Register a new user and return an access token."""

    try:
        user = user_manager.create_user(session, payload.email, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(limit_auth_attempts)])
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_db)) -> TokenResponse:
    """Authenticate a user and issue an access token."""

    user = user_manager.authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token)
