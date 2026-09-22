from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class DimensionScores(BaseModel):
    communication: float = Field(..., ge=1.0, le=4.0, description="Communication Clarity score (1-4)")
    technical: float = Field(..., ge=1.0, le=4.0, description="Technical Depth score (1-4)")
    problem_solving: float = Field(..., ge=1.0, le=4.0, description="Problem Solving & Reasoning score (1-4)")
    behavioral_star: float = Field(..., ge=1.0, le=4.0, description="Behavioral Evidence STAR score (1-4)")
    adaptability: float = Field(..., ge=1.0, le=4.0, description="Adaptability & Probing Response score (1-4)")
    confidence: float = Field(..., ge=1.0, le=4.0, description="Confidence & Composure score (1-4)")
    role_alignment: float = Field(..., ge=1.0, le=4.0, description="Role Alignment score (1-4)")

class EvaluationReportResponse(BaseModel):
    id: str
    interview_id: str
    user_id: str
    overall_score: float
    dimension_scores: DimensionScores
    strengths: List[str]
    improvement_areas: List[str]
    recommended_focus_areas: List[str]
    detailed_feedback: str
    dsa_metrics: Optional[Dict[str, Any]] = None
    topic: Optional[str] = None
    is_embedded: bool
    created_at: datetime

    model_config = {"from_attributes": True}

class CoachChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Candidate question or prompt for the AI Coach")

class CoachChatResponse(BaseModel):
    reply: str
    retrieved_sources: List[Dict[str, Any]] = []
