from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

class UserRegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters")
    full_name: str = Field(..., min_length=2, max_length=100, description="Full name of candidate")

class UserLoginRequest(BaseModel):
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="Password")

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    created_at: datetime

    model_config = {"from_attributes": True}

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse

class TokenRefreshRequest(BaseModel):
    refresh_token: str

class CandidatePersonalInfo(BaseModel):
    name: str = Field(..., min_length=1, description="Candidate full name")
    email: str | None = None
    education: str = Field(default="", description="Candidate education credential")
    experience_level: str = Field(default="", description="Experience tier")

class CandidateTargetInfo(BaseModel):
    role: str = Field(default="", description="Target role")
    company: str = Field(default="", description="Target company")

class CandidatePreferences(BaseModel):
    input_mode: str = Field(default="text", description="'text' or 'voice'")
    preferred_difficulty: str = Field(default="Adaptive AI", description="Preferred interview difficulty")

class CandidateProfileSchema(BaseModel):
    is_configured: bool = Field(default=False, description="Whether candidate has set profile")
    personal: CandidatePersonalInfo
    target: CandidateTargetInfo
    skills: list[str] = Field(default_factory=list, description="Technical skill keywords")
    preferences: CandidatePreferences
