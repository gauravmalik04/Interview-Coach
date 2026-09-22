from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class StartInterviewRequest(BaseModel):
    topic: str = Field(default="Arrays & Hashing", description="Technical topic for the interview")
    interview_mode: str = Field(default="real", description="Interview mode: 'coached' or 'real'")
    language: str = Field(default="python", description="Preferred coding language (e.g. python, javascript, java, cpp, go)")

class TurnMessage(BaseModel):
    role: str = Field(..., description="Role: 'ai' or 'candidate'")
    content: str = Field(..., description="Message content")
    timestamp: str = Field(default="", description="ISO timestamp")

class InterviewSessionResponse(BaseModel):
    id: str
    user_id: str
    topic: str
    interview_mode: str = "real"
    language: str = "python"
    status: str
    current_phase: str
    elapsed_seconds: int = 0
    started_at: datetime
    ended_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

class InterviewSessionDetailResponse(InterviewSessionResponse):
    transcript: List[Dict[str, Any]] = []
    boilerplate_code: Optional[str] = None

class UpdateTimerRequest(BaseModel):
    elapsed_seconds: int = Field(default=0, ge=0, description="Elapsed time in seconds for the session")

class WebSocketMessage(BaseModel):
    type: str  # candidate_reply, ping, token, phase_change, interview_complete, error
    content: Optional[str] = None
    phase: Optional[str] = None
    message: Optional[str] = None

class CandidateReplyRequest(BaseModel):
    content: str = Field(..., min_length=1, description="Candidate response text")

class CandidateReplyResponse(BaseModel):
    session_id: str
    ai_reply: str
    phase: str
    is_complete: bool
    boilerplate_code: Optional[str] = None
    timestamp: str

