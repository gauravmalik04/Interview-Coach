import json
import logging
from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from backend.database import get_db
from backend.models.user import User
from backend.models.coach import CoachConversation, CoachMessage
from backend.schemas.coach import (
    CoachConversationSummary,
    CoachConversationDetail,
    CoachMessageResponse,
    CreateConversationRequest,
    SendMessageRequest,
    UpdateConversationRequest,
)
from backend.agents.hermes_agent import hermes_agent
from backend.core.dependencies import get_current_user

logger = logging.getLogger("ai_interview.coach_router")

router = APIRouter(prefix="/coach", tags=["AI Mentor Hermes"])

def _format_message(msg: CoachMessage) -> CoachMessageResponse:
    citations = []
    if msg.evaluation_citations_json:
        try:
            citations = json.loads(msg.evaluation_citations_json)
        except Exception:
            citations = []
    return CoachMessageResponse(
        id=msg.id,
        conversation_id=msg.conversation_id,
        sender=msg.sender,
        content=msg.content,
        evaluation_citations=citations,
        created_at=msg.created_at
    )

@router.get("/conversations", response_model=List[CoachConversationSummary])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all previous mentorship conversations for the candidate."""
    result = await db.execute(
        select(CoachConversation)
        .options(selectinload(CoachConversation.messages))
        .where(CoachConversation.user_id == current_user.id)
        .order_by(desc(CoachConversation.updated_at))
    )
    conversations = result.scalars().all()

    summaries = []
    for conv in conversations:
        msgs = conv.messages or []
        last_msg = msgs[-1].content if msgs else ""
        if len(last_msg) > 90:
            last_msg = last_msg[:87] + "..."
        summaries.append(CoachConversationSummary(
            id=conv.id,
            title=conv.title,
            topic=conv.topic,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            message_count=len(msgs),
            last_message_preview=last_msg
        ))
    return summaries

@router.post("/conversations", response_model=CoachConversationDetail, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: CreateConversationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start a new mentorship conversation with Hermes."""
    init_topic = payload.topic or "General Guidance"
    title = f"{init_topic} Mentorship" if payload.topic else "New Mentorship Session"

    has_initial_prompt = bool(payload.initial_prompt and payload.initial_prompt.strip())
    if has_initial_prompt:
        query_text = payload.initial_prompt.strip()
        first_line = query_text.split("\n")[0][:45]
        title = first_line

        chat_hist = [{"sender": "user", "content": query_text}]

        # Generate Hermes response before opening SQLite write transaction
        hermes_res = await hermes_agent.generate_response(
            candidate_id=current_user.id,
            user_query=query_text,
            chat_history=chat_hist,
            db=db
        )

        detected_topic = hermes_res.get("topic", init_topic)

        conversation = CoachConversation(
            user_id=current_user.id,
            title=title,
            topic=detected_topic,
        )
        db.add(conversation)
        await db.flush()

        messages = []
        user_msg = CoachMessage(
            conversation_id=conversation.id,
            sender="user",
            content=query_text,
        )
        db.add(user_msg)
        messages.append(user_msg)

        hermes_msg = CoachMessage(
            conversation_id=conversation.id,
            sender="hermes",
            content=hermes_res["content"],
            evaluation_citations_json=json.dumps(hermes_res.get("citations", [])),
        )
        db.add(hermes_msg)
        messages.append(hermes_msg)

        await db.commit()
        await db.refresh(conversation)

        return CoachConversationDetail(
            id=conversation.id,
            title=conversation.title,
            topic=conversation.topic,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            messages=[_format_message(m) for m in messages]
        )
    else:
        # Base/empty chat start: No predefined static query, no synthetic messages!
        conversation = CoachConversation(
            user_id=current_user.id,
            title=title,
            topic=init_topic,
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)

        return CoachConversationDetail(
            id=conversation.id,
            title=conversation.title,
            topic=conversation.topic,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            messages=[]
        )

@router.get("/conversations/{conversation_id}", response_model=CoachConversationDetail)
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve full history and messages of a specific mentorship conversation."""
    result = await db.execute(
        select(CoachConversation)
        .options(selectinload(CoachConversation.messages))
        .where(
            CoachConversation.id == conversation_id,
            CoachConversation.user_id == current_user.id
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mentorship conversation not found"
        )

    return CoachConversationDetail(
        id=conversation.id,
        title=conversation.title,
        topic=conversation.topic,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[_format_message(m) for m in conversation.messages]
    )

@router.patch("/conversations/{conversation_id}", response_model=CoachConversationSummary)
@router.put("/conversations/{conversation_id}", response_model=CoachConversationSummary)
async def update_conversation(
    conversation_id: str,
    payload: UpdateConversationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rename a mentorship conversation."""
    result = await db.execute(
        select(CoachConversation)
        .options(selectinload(CoachConversation.messages))
        .where(
            CoachConversation.id == conversation_id,
            CoachConversation.user_id == current_user.id
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mentorship conversation not found"
        )

    clean_title = payload.title.strip()
    if not clean_title:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Title cannot be empty"
        )

    conversation.title = clean_title
    conversation.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(conversation)

    msgs = conversation.messages or []
    last_msg = msgs[-1].content if msgs else ""
    if len(last_msg) > 90:
        last_msg = last_msg[:87] + "..."

    return CoachConversationSummary(
        id=conversation.id,
        title=conversation.title,
        topic=conversation.topic,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=len(msgs),
        last_message_preview=last_msg
    )

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a mentorship conversation thread."""
    result = await db.execute(
        select(CoachConversation).where(
            CoachConversation.id == conversation_id,
            CoachConversation.user_id == current_user.id
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mentorship conversation not found"
        )

    await db.delete(conversation)
    await db.commit()
    logger.info(f"Deleted coach conversation {conversation_id} for user {current_user.id}")
    return {"status": "success", "message": "Conversation deleted successfully", "id": conversation_id}

@router.post("/conversations/{conversation_id}/messages", response_model=CoachMessageResponse)
async def send_message(
    conversation_id: str,
    payload: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a message to Hermes and receive personalized, evaluation-grounded guidance."""
    result = await db.execute(
        select(CoachConversation)
        .options(selectinload(CoachConversation.messages))
        .where(
            CoachConversation.id == conversation_id,
            CoachConversation.user_id == current_user.id
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mentorship conversation not found"
        )

    clean_content = payload.content.strip()

    # Build chat history for Hermes context
    chat_history = [
        {"sender": m.sender, "content": m.content}
        for m in conversation.messages
    ]
    chat_history.append({"sender": "user", "content": clean_content})

    # Generate Hermes response grounded in vector database evaluations
    hermes_res = await hermes_agent.generate_response(
        candidate_id=current_user.id,
        user_query=clean_content,
        chat_history=chat_history,
        db=db
    )

    # Save user message and Hermes response in single transaction
    user_msg = CoachMessage(
        conversation_id=conversation.id,
        sender="user",
        content=clean_content
    )
    db.add(user_msg)

    hermes_msg = CoachMessage(
        conversation_id=conversation.id,
        sender="hermes",
        content=hermes_res["content"],
        evaluation_citations_json=json.dumps(hermes_res.get("citations", [])),
    )
    db.add(hermes_msg)

    conversation.updated_at = datetime.now(timezone.utc)
    if hermes_res.get("topic") and conversation.topic in [None, "General Guidance", "Technical Mentorship"]:
        conversation.topic = hermes_res["topic"]
    if conversation.title in ["New Mentorship Session", "General Guidance Mentorship", "General Guidance"]:
        first_prompt = clean_content.split("\n")[0][:45]
        conversation.title = first_prompt

    await db.commit()
    await db.refresh(hermes_msg)

    return _format_message(hermes_msg)
