import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.interview import InterviewSession
from backend.services.question_loader import question_loader, QuestionItem
from backend.agents.interview_agent import dsa_interview_agent

logger = logging.getLogger("ai_interview.engine")

PHASES = ["intro", "warm_up", "core", "probing", "closing", "done"]

class InterviewEngine:
    """Service to orchestrate adaptive DSA interview state progression and dialogue turns."""

    def get_initial_greeting(self, session: InterviewSession) -> str:
        """Generate introductory welcome message for a DSA interview session."""
        mode_label = "Coached Mock Interview" if getattr(session, "interview_mode", "real") == "coached" else "Technical Mock Interview"
        coached_note = ""
        if getattr(session, "interview_mode", "real") == "coached":
            coached_note = (
                "\n\n> 💡 **Coached Mode Active**:\n"
                "> You will receive real-time expectation callouts and structured answering advice throughout this interview. "
                "The scratchpad on the right has runnable starter code in your chosen language!"
            )

        if "general" in session.topic.lower():
            return (
                f"Welcome to your **{mode_label}**!\n\n"
                f"I'm your AI technical interviewer. In this session, problems will be drawn dynamically across core topics "
                f"(Arrays, Trees, Graphs, Dynamic Programming, and more) to simulate a comprehensive coding interview.\n\n"
                f"When you're ready, please introduce yourself briefly and let me know which areas you have prepared."
                f"{coached_note}"
            )
        return (
            f"Welcome to your **{mode_label}** on **{session.topic}**!\n\n"
            f"I'm your AI technical interviewer. In this session, we will tackle algorithmic problems, "
            f"evaluate your problem-solving approach, and analyze time/space complexities.\n\n"
            f"When you're ready, please introduce yourself briefly and mention your comfort level with {session.topic}."
            f"{coached_note}"
        )

    def _get_questions_for_topic(self, topic: str) -> List[QuestionItem]:
        """Fetch questions for the specified topic from the question loader."""
        questions = question_loader.get_questions_by_category(topic)
        if not questions:
            questions = question_loader.get_all_questions()
        return questions

    async def process_candidate_turn(
        self,
        session: InterviewSession,
        candidate_text: str,
        db: AsyncSession,
    ) -> Tuple[str, str, bool, Optional[str]]:
        """
        Process candidate response, update transcript, advance phase, and dynamically generate next AI turn
        using the LLM agent.
        Returns: (ai_response_text, new_phase, is_complete, target_boilerplate)
        """
        # Parse transcript
        try:
            transcript: List[Dict[str, Any]] = json.loads(session.transcript_json) if session.transcript_json else []
        except Exception:
            transcript = []

        now_iso = datetime.now(timezone.utc).isoformat()

        # Append candidate message
        transcript.append({
            "role": "candidate",
            "content": candidate_text.strip(),
            "timestamp": now_iso
        })

        questions = self._get_questions_for_topic(session.topic)
        current_phase = session.current_phase or "intro"
        is_complete = False

        # Phase progression machine
        if current_phase == "intro":
            next_phase = "warm_up"
            target_q = questions[0] if questions else None
        elif current_phase == "warm_up":
            next_phase = "core"
            target_q = questions[1] if len(questions) > 1 else (questions[0] if questions else None)
        elif current_phase == "core":
            next_phase = "probing"
            target_q = questions[1] if len(questions) > 1 else (questions[0] if questions else None)
        elif current_phase == "probing":
            next_phase = "closing"
            target_q = None
        elif current_phase in ("closing", "done"):
            next_phase = "done"
            target_q = None
            is_complete = True
        else:
            next_phase = "done"
            target_q = None
            is_complete = True

        mode = getattr(session, "interview_mode", "real") or "real"

        # Dynamically generate AI response using the LangGraph DSA agent
        try:
            ai_text = await dsa_interview_agent.generate_response(
                topic=session.topic,
                phase=next_phase,
                candidate_text=candidate_text,
                transcript=transcript,
                target_question=target_q,
                interview_mode=mode,
            )
        except Exception as e:
            logger.error(f"Error in dsa_interview_agent: {e}", exc_info=True)
            ai_text = dsa_interview_agent._heuristic_dsa_response(
                topic=session.topic,
                phase=next_phase,
                candidate_text=candidate_text,
                target_question=target_q,
                interview_mode=mode,
            )

        # Append AI response to transcript
        transcript.append({
            "role": "ai",
            "content": ai_text,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        # Track active question ID and boilerplate
        target_boilerplate = None
        if target_q:
            session.current_question_id = target_q.id
            from backend.services.boilerplate_service import boilerplate_service
            target_boilerplate = boilerplate_service.get_boilerplate(
                question_id=target_q.id,
                language=session.language or "python",
                topic=session.topic,
                question_item=target_q,
            )

        # Update session in DB
        session.current_phase = next_phase
        session.transcript_json = json.dumps(transcript)
        if is_complete:
            session.status = "completed"
            session.ended_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(session)

        return ai_text, next_phase, is_complete, target_boilerplate

    async def ensure_initial_message(self, session: InterviewSession, db: AsyncSession) -> Tuple[str, str]:
        """Ensure the session has an initial greeting message in the transcript."""
        try:
            transcript: List[Dict[str, Any]] = json.loads(session.transcript_json) if session.transcript_json else []
        except Exception:
            transcript = []

        if not transcript:
            greeting = self.get_initial_greeting(session)
            transcript.append({
                "role": "ai",
                "content": greeting,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            session.transcript_json = json.dumps(transcript)
            session.current_phase = "intro"
            await db.commit()
            await db.refresh(session)
            return greeting, "intro"

        latest_ai_msg = ""
        for m in reversed(transcript):
            if m.get("role") == "ai":
                latest_ai_msg = m.get("content", "")
                break
        return latest_ai_msg or self.get_initial_greeting(session), session.current_phase

interview_engine = InterviewEngine()
