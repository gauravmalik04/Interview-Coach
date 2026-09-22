from typing import List, Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class CoachCitation(BaseModel):
    topic: Optional[str] = None
    score: Optional[float] = None
    date: Optional[str] = None
    strengths: Optional[List[str]] = Field(default_factory=list)
    improvements: Optional[List[str]] = Field(default_factory=list)

class CoachMessageResponse(BaseModel):
    id: str
    conversation_id: str
    sender: str
    content: str
    evaluation_citations: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class CoachConversationSummary(BaseModel):
    id: str
    title: str
    topic: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
    last_message_preview: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class CoachConversationDetail(BaseModel):
    id: str
    title: str
    topic: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    messages: List[CoachMessageResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

class CreateConversationRequest(BaseModel):
    initial_prompt: Optional[str] = Field(default=None, description="Optional starting message for Hermes")
    topic: Optional[str] = Field(default=None, description="Target domain or topic")

class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000, description="Message to Hermes")

class UpdateConversationRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="New title for the conversation")
