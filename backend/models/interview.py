import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from backend.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class InterviewSession(Base):
    """Interview Session Model representing an ongoing or completed interview."""
    __tablename__ = "interview_sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    topic = Column(String(100), nullable=False, default="Arrays & Hashing")
    interview_mode = Column(String(20), nullable=False, default="real")  # 'coached' or 'real'
    language = Column(String(30), nullable=False, default="python")  # 'python', 'javascript', 'java', 'cpp', 'go'
    current_question_id = Column(String(50), nullable=True)  # ID of the currently asked question
    status = Column(String(50), nullable=False, default="active")  # active, paused, completed
    current_phase = Column(String(50), nullable=False, default="intro")  # intro, warm_up, core, probing, closing, done
    transcript_json = Column(Text, nullable=False, default="[]")  # JSON list of turns
    started_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="sessions")
    report = relationship("EvaluationReport", back_populates="interview", uselist=False, cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<InterviewSession id={self.id} user_id={self.user_id} status={self.status} phase={self.current_phase}>"
