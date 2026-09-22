import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from backend.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class CoachConversation(Base):
    """Stores persistent conversation threads with AI Mentor Hermes."""
    __tablename__ = "coach_conversations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    title = Column(String(255), nullable=False, default="New Mentorship Session")
    topic = Column(String(100), nullable=True, default="General Guidance")
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    user = relationship("User")
    messages = relationship(
        "CoachMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="CoachMessage.created_at"
    )

    def __repr__(self) -> str:
        return f"<CoachConversation id={self.id} title={self.title!r} user_id={self.user_id}>"

class CoachMessage(Base):
    """Stores individual conversational turns between the candidate and Hermes."""
    __tablename__ = "coach_messages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    conversation_id = Column(String(36), ForeignKey("coach_conversations.id", ondelete="CASCADE"), index=True, nullable=False)
    sender = Column(String(20), nullable=False)  # 'user' or 'hermes'
    content = Column(Text, nullable=False)
    evaluation_citations_json = Column(Text, nullable=True, default="[]")  # List of citations/metrics used
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    conversation = relationship("CoachConversation", back_populates="messages")

    def __repr__(self) -> str:
        return f"<CoachMessage id={self.id} sender={self.sender} conv={self.conversation_id}>"
