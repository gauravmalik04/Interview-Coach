import json
import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.models.interview import InterviewSession
from backend.models.report import EvaluationReport
from backend.agents.evaluator_agent import evaluator_agent
from backend.services.embedding_service import embedding_service

logger = logging.getLogger("ai_interview.evaluation_service")

class EvaluationService:
    """Service to orchestrate interview evaluation, database persistence, and vector chunking."""

    async def generate_and_save_report(
        self,
        session: InterviewSession,
        user_id: str,
        db: AsyncSession,
    ) -> EvaluationReport:
        """
        Evaluate session transcript using DSAEvaluatorAgent, persist to SQLite,
        and chunk discrete metrics into ChromaDB.
        """
        try:
            transcript = json.loads(session.transcript_json) if session.transcript_json else []
        except Exception:
            transcript = []

        logger.info(f"Generating evaluation report for interview {session.id} ({session.topic})...")
        evaluation = await evaluator_agent.evaluate_interview(
            topic=session.topic,
            transcript=transcript
        )

        # Check existing report
        result = await db.execute(
            select(EvaluationReport).where(EvaluationReport.interview_id == session.id)
        )
        report = result.scalar_one_or_none()

        scores_payload = {
            **evaluation["dimension_scores"],
            "dsa_metrics": evaluation["dsa_metrics"],
            "topic": session.topic,
        }

        if not report:
            report = EvaluationReport(
                interview_id=session.id,
                user_id=user_id,
                overall_score=evaluation["overall_score"],
                scores_json=json.dumps(scores_payload),
                strengths_json=json.dumps(evaluation["strengths"]),
                improvements_json=json.dumps(evaluation["improvement_areas"]),
                focus_areas_json=json.dumps(evaluation["recommended_focus_areas"]),
                detailed_feedback=evaluation["detailed_feedback"],
                is_embedded=False,
            )
            db.add(report)
        else:
            report.overall_score = evaluation["overall_score"]
            report.scores_json = json.dumps(scores_payload)
            report.strengths_json = json.dumps(evaluation["strengths"])
            report.improvements_json = json.dumps(evaluation["improvement_areas"])
            report.focus_areas_json = json.dumps(evaluation["recommended_focus_areas"])
            report.detailed_feedback = evaluation["detailed_feedback"]
            report.is_embedded = False

        await db.commit()
        await db.refresh(report)

        # Chunk discrete metrics into ChromaDB
        try:
            embedded = embedding_service.store_evaluation_chunks(
                candidate_id=user_id,
                interview_id=session.id,
                report_data=evaluation,
                date_str=datetime.now(timezone.utc).isoformat()
            )
            if embedded:
                report.is_embedded = True
                await db.commit()
                await db.refresh(report)
                logger.info(f"Successfully chunked and embedded evaluation for interview {session.id}.")
        except Exception as e:
            logger.error(f"Failed to embed evaluation chunks in ChromaDB: {e}", exc_info=True)

        return report

evaluation_service = EvaluationService()
