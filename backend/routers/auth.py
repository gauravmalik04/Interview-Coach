import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.user import User
from backend.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    TokenRefreshRequest,
    UserResponse,
    CandidateProfileSchema,
    CandidatePersonalInfo,
    CandidateTargetInfo,
    CandidatePreferences,
)
from backend.services.auth_service import auth_service
from backend.core.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request: UserRegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new candidate account and immediately return JWT tokens."""
    user = await auth_service.register_user(db, request)
    return auth_service.generate_token_response(user)

@router.post("/login", response_model=TokenResponse)
async def login(request: UserLoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate with email and password to receive access & refresh tokens."""
    user = await auth_service.authenticate_user(db, request.email, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return auth_service.generate_token_response(user)

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: TokenRefreshRequest, db: AsyncSession = Depends(get_db)):
    """Issue a new access token using a valid refresh token."""
    return await auth_service.refresh_tokens(db, request.refresh_token)

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get profile information of the currently authenticated candidate."""
    return current_user

@router.get("/profile", response_model=CandidateProfileSchema)
async def get_profile(current_user: User = Depends(get_current_user)):
    """Get candidate profile details. If configured in DB, returns saved details with is_configured=True."""
    if current_user.profile_data:
        try:
            data = json.loads(current_user.profile_data)
            data.setdefault("personal", {})["email"] = current_user.email
            has_edu = bool(data.get("personal", {}).get("education"))
            has_role = bool(data.get("target", {}).get("role"))
            data["is_configured"] = bool(data.get("is_configured", False) or (has_edu and has_role))
            return CandidateProfileSchema(**data)
        except Exception:
            pass

    return CandidateProfileSchema(
        is_configured=False,
        personal=CandidatePersonalInfo(
            name=current_user.full_name or "",
            email=current_user.email,
            education="",
            experience_level="",
        ),
        target=CandidateTargetInfo(
            role="",
            company="",
        ),
        skills=[],
        preferences=CandidatePreferences(
            input_mode="",
            preferred_difficulty="",
        ),
    )

@router.put("/profile", response_model=CandidateProfileSchema)
async def update_profile(
    profile: CandidateProfileSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save and persist candidate profile details, marking is_configured=True."""
    profile.personal.email = current_user.email
    profile.is_configured = True
    current_user.full_name = profile.personal.name
    current_user.profile_data = json.dumps(profile.model_dump())
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return profile

