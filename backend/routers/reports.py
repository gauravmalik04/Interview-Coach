import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from backend.database import get_db
from backend.models.user import User
from backend.models.report import EvaluationReport
from backend.schemas.report import EvaluationReportResponse, DimensionScores
from backend.core.dependencies import get_current_user

router = APIRouter(prefix="/reports", tags=["Evaluation Reports"])

def _format_report_response(report: EvaluationReport) -> EvaluationReportResponse:
    """Format DB EvaluationReport model into Pydantic response."""
    try:
        raw_scores = json.loads(report.scores_json)
    except Exception:
        raw_scores = {}

    dimension_scores = DimensionScores(
        communication=raw_scores.get("communication", 1.0),
        technical=raw_scores.get("technical", 1.0),
        problem_solving=raw_scores.get("problem_solving", 1.0),
        behavioral_star=raw_scores.get("behavioral_star", 1.0),
        adaptability=raw_scores.get("adaptability", 1.0),
        confidence=raw_scores.get("confidence", 1.0),
        role_alignment=raw_scores.get("role_alignment", 1.0),
    )

    try:
        strengths = json.loads(report.strengths_json) if report.strengths_json else []
    except Exception:
        strengths = []

    try:
        improvements = json.loads(report.improvements_json) if report.improvements_json else []
    except Exception:
        improvements = []

    try:
        focus_areas = json.loads(report.focus_areas_json) if report.focus_areas_json else []
    except Exception:
        focus_areas = []

    dsa_metrics = raw_scores.get("dsa_metrics")
    topic = raw_scores.get("topic")

    return EvaluationReportResponse(
        id=report.id,
        interview_id=report.interview_id,
        user_id=report.user_id,
        overall_score=report.overall_score,
        dimension_scores=dimension_scores,
        dsa_metrics=dsa_metrics,
        topic=topic,
        strengths=strengths,
        improvement_areas=improvements,
        recommended_focus_areas=focus_areas,
        detailed_feedback=report.detailed_feedback,
        is_embedded=report.is_embedded,
        created_at=report.created_at,
    )

@router.get("/", response_model=List[EvaluationReportResponse])
async def list_reports(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all evaluation reports for the current candidate."""
    result = await db.execute(
        select(EvaluationReport)
        .where(EvaluationReport.user_id == current_user.id)
        .order_by(desc(EvaluationReport.created_at))
    )
    reports = result.scalars().all()
    return [_format_report_response(r) for r in reports]

@router.post("/generate/{interview_id}", response_model=EvaluationReportResponse)
async def generate_report_endpoint(
    interview_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate or re-generate an evaluation report for an interview session and chunk to ChromaDB."""
    from backend.models.interview import InterviewSession
    from backend.services.evaluation_service import evaluation_service

    result = await db.execute(
        select(InterviewSession).where(
            InterviewSession.id == interview_id,
            InterviewSession.user_id == current_user.id
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview session not found"
        )

    report = await evaluation_service.generate_and_save_report(session, current_user.id, db)
    return _format_report_response(report)

@router.get("/{interview_id}", response_model=EvaluationReportResponse)
async def get_report_by_interview(
    interview_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve evaluation report for a specific interview session."""
    result = await db.execute(
        select(EvaluationReport)
        .where(
            EvaluationReport.interview_id == interview_id,
            EvaluationReport.user_id == current_user.id
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation report not found for this interview session"
        )
    return _format_report_response(report)
