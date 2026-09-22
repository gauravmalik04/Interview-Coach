import json
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select

from backend.database import AsyncSessionLocal
from backend.models.interview import InterviewSession
from backend.core.dependencies import get_user_from_token_str
from backend.services.interview_engine import interview_engine

logger = logging.getLogger("ai_interview.websocket")

router = APIRouter(tags=["Interview WebSocket"])

@router.websocket("/ws/interview/{session_id}")
async def interview_websocket_endpoint(websocket: WebSocket, session_id: str):
    """Real-time WebSocket endpoint for candidate-AI technical interview interaction."""
    token: Optional[str] = websocket.query_params.get("token")
    
    await websocket.accept()

    async with AsyncSessionLocal() as db:
        user = await get_user_from_token_str(token, db) if token else None

        # Fallback: wait for auth message if token wasn't in query params
        if not user:
            try:
                auth_data = await websocket.receive_json()
                if auth_data.get("type") == "auth" and auth_data.get("token"):
                    user = await get_user_from_token_str(auth_data["token"], db)
            except Exception:
                user = None

        if not user:
            logger.warning(f"Unauthorized WebSocket connection attempt for session {session_id}")
            await websocket.send_json({"type": "error", "message": "Unauthorized or expired authentication token."})
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # Fetch session
        result = await db.execute(
            select(InterviewSession).where(
                InterviewSession.id == session_id,
                InterviewSession.user_id == user.id,
            )
        )
        session = result.scalar_one_or_none()

        if not session:
            logger.warning(f"Interview session {session_id} not found for user {user.id}")
            await websocket.send_json({"type": "error", "message": "Interview session not found."})
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        session_mode = session.interview_mode or "real"
        session_user_id = user.id

        # Ensure initial AI welcome message exists
        initial_ai_text, phase = await interview_engine.ensure_initial_message(session, db)

        # Send session initialization event with full transcript history
        try:
            transcript = json.loads(session.transcript_json) if session.transcript_json else []
        except Exception:
            transcript = []

        await websocket.send_json({
            "type": "session_init",
            "session_id": session.id,
            "topic": session.topic,
            "phase": session.current_phase,
            "status": session.status,
            "transcript": transcript,
        })

    # Main WebSocket interaction loop
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            elif msg_type == "candidate_reply":
                content = data.get("content", "").strip()
                if not content:
                    continue

                # Process turn in a clean DB session
                async with AsyncSessionLocal() as db:
                    result = await db.execute(
                        select(InterviewSession).where(
                            InterviewSession.id == session_id,
                            InterviewSession.user_id == user.id,
                        )
                    )
                    curr_session = result.scalar_one_or_none()
                    if not curr_session:
                        await websocket.send_json({"type": "error", "message": "Session no longer active."})
                        break

                    ai_text, next_phase, is_complete, target_boilerplate = await interview_engine.process_candidate_turn(
                        curr_session, content, db
                    )

                # Send AI message response with asked question's starter code
                await websocket.send_json({
                    "type": "agent_message",
                    "content": ai_text,
                    "phase": next_phase,
                    "boilerplate_code": target_boilerplate,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

                if is_complete:
                    await websocket.send_json({
                        "type": "interview_complete",
                        "session_id": session_id,
                        "phase": "done",
                        "message": "Interview session completed successfully."
                    })
                    break

            elif msg_type == "finish":
                # Explicit end interview requested
                async with AsyncSessionLocal() as db:
                    result = await db.execute(
                        select(InterviewSession).where(
                            InterviewSession.id == session_id,
                            InterviewSession.user_id == user.id,
                        )
                    )
                    curr_session = result.scalar_one_or_none()
                    if curr_session:
                        curr_session.status = "completed"
                        curr_session.current_phase = "done"
                        curr_session.ended_at = datetime.now(timezone.utc)
                        await db.commit()

                await websocket.send_json({
                    "type": "interview_complete",
                    "session_id": session_id,
                    "phase": "done",
                    "message": "Interview concluded."
                })
                break

    except WebSocketDisconnect:
        logger.info(f"Candidate disconnected WebSocket from interview session {session_id}")
        # Real-mode interviews cannot be left in between; closing or disconnecting ends them immediately
        if 'session_mode' in locals() and session_mode == "real" and 'session_user_id' in locals():
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(InterviewSession).where(
                        InterviewSession.id == session_id,
                        InterviewSession.user_id == session_user_id,
                    )
                )
                curr_session = result.scalar_one_or_none()
                if curr_session and curr_session.status != "completed":
                    curr_session.status = "completed"
                    curr_session.current_phase = "done"
                    if not curr_session.ended_at:
                        curr_session.ended_at = datetime.now(timezone.utc)
                    await db.commit()
    except Exception as e:
        logger.error(f"WebSocket error during session {session_id}: {e}", exc_info=True)
        try:
            await websocket.send_json({"type": "error", "message": "An unexpected connection error occurred."})
        except Exception:
            pass
