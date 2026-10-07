from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.entities import User
from app.repositories.user_repository import UserRepository
from app.api.dependencies import get_user_repo, get_current_user
from app.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)

router = APIRouter(prefix="/api/auth", tags=["Auth"])

class UserRegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="Password (at least 6 characters)")
    full_name: Optional[str] = Field(default="", description="Full name of the user")

class UserLoginRequest(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="Password")

class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="Valid JWT refresh token")

class UserProfileResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = ""
    created_at: Optional[str] = None

class AuthTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserProfileResponse


@router.post("/register", response_model=AuthTokenResponse, status_code=status.HTTP_201_CREATED, summary="Register a new user account")
async def register(
    req: UserRegisterRequest,
    user_repo: UserRepository = Depends(get_user_repo)
):
    email = req.email.strip().lower()
    existing = await user_repo.get_by_email(email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists."
        )

    hashed_pwd = hash_password(req.password)
    user = await user_repo.create(
        email=email,
        hashed_password=hashed_pwd,
        full_name=req.full_name.strip() if req.full_name else ""
    )

    access_token = create_access_token(data={"sub": user.id, "email": user.email})
    refresh_token = create_refresh_token(data={"sub": user.id, "email": user.email})

    return AuthTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=UserProfileResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            created_at=user.created_at.isoformat() if user.created_at else None
        )
    )


@router.post("/login", response_model=AuthTokenResponse, summary="Log in with email and password")
async def login(
    req: UserLoginRequest,
    user_repo: UserRepository = Depends(get_user_repo)
):
    email = req.email.strip().lower()
    user = await user_repo.get_by_email(email)
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    access_token = create_access_token(data={"sub": user.id, "email": user.email})
    refresh_token = create_refresh_token(data={"sub": user.id, "email": user.email})

    return AuthTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=UserProfileResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            created_at=user.created_at.isoformat() if user.created_at else None
        )
    )


@router.post("/refresh", summary="Generate a new access token using a valid refresh token")
async def refresh_tokens(
    req: RefreshTokenRequest,
    user_repo: UserRepository = Depends(get_user_repo)
):
    payload = decode_token(req.refresh_token, expected_type="refresh")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token payload.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    new_access_token = create_access_token(data={"sub": user.id, "email": user.email})
    new_refresh_token = create_refresh_token(data={"sub": user.id, "email": user.email})

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=UserProfileResponse, summary="Get current authenticated user profile")
async def get_me(current_user: User = Depends(get_current_user)):
    return UserProfileResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        created_at=current_user.created_at.isoformat() if current_user.created_at else None
    )
