import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Float, Boolean
from sqlalchemy.orm import relationship

from backend.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class EvaluationReport(Base):
    """Evaluation Report Model storing the 7-dimension scores and AI feedback."""
    __tablename__ = "evaluation_reports"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    interview_id = Column(String(36), ForeignKey("interview_sessions.id", ondelete="CASCADE"), unique=True, nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    
    overall_score = Column(Float, nullable=False)  # 1.0 to 4.0
    scores_json = Column(Text, nullable=False)     # {"communication": 3.0, "technical": 4.0, ...}
    strengths_json = Column(Text, nullable=False, default="[]")
    improvements_json = Column(Text, nullable=False, default="[]")
    focus_areas_json = Column(Text, nullable=False, default="[]")
    detailed_feedback = Column(Text, nullable=False, default="")
    is_embedded = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    interview = relationship("InterviewSession", back_populates="report")
    user = relationship("User", back_populates="reports")

    def __repr__(self) -> str:
        return f"<EvaluationReport id={self.id} interview_id={self.interview_id} score={self.overall_score}>"
