import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from backend.database import get_db, AsyncSessionLocal
from backend.models.user import User
from backend.models.interview import InterviewSession
from backend.schemas.interview import (
    StartInterviewRequest,
    InterviewSessionResponse,
    InterviewSessionDetailResponse,
    CandidateReplyRequest,
    CandidateReplyResponse,
    UpdateTimerRequest,
)
from backend.core.dependencies import get_current_user, get_user_from_token_str
from backend.services.interview_engine import interview_engine
from backend.services.boilerplate_service import boilerplate_service

logger = logging.getLogger("ai_interview.sessions")

router = APIRouter(prefix="/sessions", tags=["Interview Sessions"])



@router.post("/start", response_model=InterviewSessionResponse, status_code=status.HTTP_201_CREATED)
async def start_session(
    request: StartInterviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start a new interview session for the authenticated candidate."""
    session = InterviewSession(
        user_id=current_user.id,
        topic=request.topic,
        interview_mode=request.interview_mode or "real",
        language=request.language or "python",
        status="active",
        current_phase="intro",
        transcript_json="[]",
        started_at=datetime.now(timezone.utc),
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    
    # Pre-populate greeting
    await interview_engine.ensure_initial_message(session, db)
    return session

@router.get("/", response_model=List[InterviewSessionResponse])
async def list_candidate_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all interview sessions for the logged-in candidate."""
    result = await db.execute(
        select(InterviewSession)
        .where(InterviewSession.user_id == current_user.id)
        .order_by(desc(InterviewSession.started_at))
    )
    return result.scalars().all()

@router.get("/active")
async def get_active_interview_session(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve the most recent active interview session that can be resumed.
    Real-mode interviews cannot be left in between; if any real interview was left active,
    it is automatically finalized on the spot and cannot be resumed.
    Only coached-mode interviews can be resumed.
    """
    result = await db.execute(
        select(InterviewSession)
        .where(
            InterviewSession.user_id == current_user.id,
            InterviewSession.status == "active",
        )
        .order_by(desc(InterviewSession.started_at))
    )
    active_sessions = result.scalars().all()

    resumable_session = None
    has_changes = False
    for sess in active_sessions:
        if sess.interview_mode == "real":
            # Real interviews cannot be left in between; end immediately
            sess.status = "completed"
            sess.current_phase = "done"
            if not sess.ended_at:
                sess.ended_at = datetime.now(timezone.utc)
            db.add(sess)
            has_changes = True
        elif sess.interview_mode == "coached" and not resumable_session:
            resumable_session = sess

    if has_changes:
        await db.commit()

    if resumable_session:
        return {
            "has_active": True,
            "session_id": resumable_session.id,
            "topic": resumable_session.topic,
            "interview_mode": resumable_session.interview_mode,
            "phase": resumable_session.current_phase,
        }

    return {"has_active": False, "session_id": None}

@router.get("/{session_id}", response_model=InterviewSessionDetailResponse)
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get details and transcript for a specific interview session."""
    result = await db.execute(
        select(InterviewSession)
        .where(
            InterviewSession.id == session_id,
            InterviewSession.user_id == current_user.id
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview session not found"
        )

    # Ensure greeting exists
    await interview_engine.ensure_initial_message(session, db)

    transcript_list = []
    try:
        transcript_list = json.loads(session.transcript_json) if session.transcript_json else []
    except Exception:
        transcript_list = []

    # Resolve boilerplate code for the active/asked question
    starter_code = None
    if session.current_question_id:
        starter_code = boilerplate_service.get_boilerplate(
            question_id=session.current_question_id,
            language=session.language or "python",
            topic=session.topic,
        )
    elif session.current_phase == "intro":
        starter_code = boilerplate_service.get_intro_placeholder(session.language or "python")
    else:
        questions = interview_engine._get_questions_for_topic(session.topic)
        target_q = questions[0] if questions else None
        if session.current_phase in ("core", "probing") and len(questions) > 1:
            target_q = questions[1]
        starter_code = boilerplate_service.get_boilerplate(
            question_id=target_q.id if target_q else None,
            language=session.language or "python",
            topic=session.topic,
            question_item=target_q,
        )

    def _to_aware_utc(dt: Optional[datetime]) -> Optional[datetime]:
        if dt and dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    return InterviewSessionDetailResponse(
        id=session.id,
        user_id=session.user_id,
        topic=session.topic,
        interview_mode=session.interview_mode or "real",
        language=session.language or "python",
        status=session.status,
        current_phase=session.current_phase,
        elapsed_seconds=session.elapsed_seconds or 0,
        started_at=_to_aware_utc(session.started_at),
        ended_at=_to_aware_utc(session.ended_at),
        transcript=transcript_list,
        boilerplate_code=starter_code,
    )

@router.get("/{session_id}/boilerplate")
async def get_session_boilerplate(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve runnable starter code for the session's active question and chosen language."""
    result = await db.execute(
        select(InterviewSession).where(
            InterviewSession.id == session_id,
            InterviewSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview session not found"
        )
    
    qid = session.current_question_id
    starter_code = None
    if qid:
        starter_code = boilerplate_service.get_boilerplate(
            question_id=qid,
            language=session.language or "python",
            topic=session.topic,
        )
    elif session.current_phase == "intro":
        starter_code = boilerplate_service.get_intro_placeholder(session.language or "python")
    else:
        questions = interview_engine._get_questions_for_topic(session.topic)
        target_q = questions[0] if questions else None
        if session.current_phase in ("core", "probing") and len(questions) > 1:
            target_q = questions[1]
        starter_code = boilerplate_service.get_boilerplate(
            question_id=target_q.id if target_q else None,
            language=session.language or "python",
            topic=session.topic,
            question_item=target_q,
        )

    return {
        "session_id": session.id,
        "language": session.language or "python",
        "question_id": qid,
        "boilerplate_code": starter_code,
    }

@router.post("/{session_id}/reply", response_model=CandidateReplyResponse)
async def submit_candidate_reply(
    session_id: str,
    body: CandidateReplyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """HTTP fallback endpoint for candidate to submit an answer and receive next AI turn."""
    result = await db.execute(
        select(InterviewSession).where(
            InterviewSession.id == session_id,
            InterviewSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview session not found"
        )
    if session.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Interview session has already been completed."
        )

    ai_reply, next_phase, is_complete, target_boilerplate = await interview_engine.process_candidate_turn(
        session, body.content, db
    )


    return CandidateReplyResponse(
        session_id=session.id,
        ai_reply=ai_reply,
        phase=next_phase,
        is_complete=is_complete,
        boilerplate_code=target_boilerplate,
        timestamp=datetime.now(timezone.utc).isoformat()
    )

@router.post("/{session_id}/finish")
async def finish_interview_session(
    session_id: str,
    token: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """Explicitly mark interview session as completed and generate evaluation report.
    Supports Bearer header or token query parameter for beacon unloads.
    """
    current_user = None
    if authorization and authorization.startswith("Bearer "):
        current_user = await get_user_from_token_str(authorization.split(" ")[1], db)
    elif token:
        current_user = await get_user_from_token_str(token, db)
    
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

    result = await db.execute(
        select(InterviewSession).where(
            InterviewSession.id == session_id,
            InterviewSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview session not found"
        )

    session.status = "completed"
    session.current_phase = "done"
    if not session.ended_at:
        session.ended_at = datetime.now(timezone.utc)
    await db.commit()

    return {
        "session_id": session.id,
        "status": "completed",
        "phase": "done",
    }

@router.post("/{session_id}/timer")
async def update_session_timer(
    session_id: str,
    body: Optional[UpdateTimerRequest] = None,
    seconds: Optional[int] = Query(None),
    token: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """Save the elapsed timer seconds for an interview session."""
    current_user = None
    if authorization and authorization.startswith("Bearer "):
        current_user = await get_user_from_token_str(authorization.split(" ")[1], db)
    elif token:
        current_user = await get_user_from_token_str(token, db)
    
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

    result = await db.execute(
        select(InterviewSession).where(
            InterviewSession.id == session_id,
            InterviewSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview session not found"
        )

    sec_val = None
    if body and body.elapsed_seconds is not None:
        sec_val = body.elapsed_seconds
    elif seconds is not None:
        sec_val = seconds

    if sec_val is not None and sec_val >= 0:
        session.elapsed_seconds = max(session.elapsed_seconds or 0, sec_val)
        await db.commit()

    return {
        "session_id": session.id,
        "elapsed_seconds": session.elapsed_seconds or 0,
    }

