import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from backend.models.user import User
from backend.schemas.auth import UserRegisterRequest, TokenResponse, UserResponse
from backend.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token

logger = logging.getLogger("ai_interview.auth_service")

class AuthService:
    """Handles candidate registration, password validation, and token lifecycle."""

    async def register_user(self, db: AsyncSession, request: UserRegisterRequest) -> User:
        """Register a new candidate user."""
        # Check if email already exists
        existing_result = await db.execute(select(User).where(User.email == request.email.lower()))
        existing = existing_result.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email already exists"
            )

        new_user = User(
            email=request.email.lower(),
            hashed_password=hash_password(request.password),
            full_name=request.full_name.strip()
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        logger.info(f"Registered new candidate user: {new_user.email} (id: {new_user.id})")
        return new_user

    async def authenticate_user(self, db: AsyncSession, email: str, password: str) -> Optional[User]:
        """Authenticate user by email and password."""
        result = await db.execute(select(User).where(User.email == email.lower()))
        user = result.scalar_one_or_none()
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def generate_token_response(self, user: User) -> TokenResponse:
        """Create access and refresh tokens for authenticated user."""
        token_data = {"sub": user.id, "email": user.email}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=UserResponse.model_validate(user)
        )

    async def refresh_tokens(self, db: AsyncSession, refresh_token_str: str) -> TokenResponse:
        """Validate refresh token and issue a fresh pair of tokens."""
        payload = decode_token(refresh_token_str)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )

        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User no longer exists"
            )

        return self.generate_token_response(user)

auth_service = AuthService()
