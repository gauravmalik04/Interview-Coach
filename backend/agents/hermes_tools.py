import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from backend.models.report import EvaluationReport
from backend.models.interview import InterviewSession
from backend.services.embedding_service import embedding_service
from backend.services.question_loader import question_loader

logger = logging.getLogger("ai_interview.hermes_tools")

# Standard DSA metric keys recognized by the evaluation system
METRIC_ALIASES = {
    "edge_cases": ["edge case", "edge cases", "boundary", "boundaries", "null check", "empty input", "corner case"],
    "complexity": ["complexity", "big-o", "big o", "time complexity", "space complexity", "runtime", "space"],
    "correctness": ["correctness", "bug", "logic", "accuracy", "algorithm", "algorithmic"],
    "data_structures": ["data structure", "data structures", "ds", "hashmap", "heap", "stack", "queue"],
    "code_quality": ["code quality", "clean code", "style", "naming", "modularity", "implementation"],
    "problem_solving": ["problem solving", "reasoning", "approach", "optimization", "pattern"],
    "communication": ["communication", "verbal", "collaboration", "explaining", "clarifying"]
}

def _parse_report(rep: EvaluationReport, sess: Optional[InterviewSession] = None) -> Dict[str, Any]:
    """Helper to deserialize an EvaluationReport into a clean dictionary."""
    scores_dict = {}
    try:
        scores_dict = json.loads(rep.scores_json) if rep.scores_json else {}
    except Exception:
        scores_dict = {}

    strengths = []
    try:
        strengths = json.loads(rep.strengths_json) if rep.strengths_json else []
    except Exception:
        strengths = []

    improvements = []
    try:
        improvements = json.loads(rep.improvements_json) if rep.improvements_json else []
    except Exception:
        improvements = []

    focus_areas = []
    try:
        focus_areas = json.loads(rep.focus_areas_json) if rep.focus_areas_json else []
    except Exception:
        focus_areas = []

    date_str = rep.created_at.strftime("%b %d, %Y") if rep.created_at else "Recent"
    topic = sess.topic if sess and sess.topic else scores_dict.get("topic", "Technical DSA")
    mode = sess.interview_mode if sess and getattr(sess, "interview_mode", None) else "real"

    return {
        "report_id": rep.id,
        "interview_id": rep.interview_id,
        "topic": topic,
        "interview_mode": mode,
        "overall_score": rep.overall_score,
        "date": date_str,
        "strengths": strengths,
        "improvements": improvements,
        "focus_areas": focus_areas,
        "detailed_feedback": rep.detailed_feedback or "",
        "dsa_metrics": scores_dict.get("dsa_metrics", {}),
        "scores_dict": scores_dict
    }

async def get_candidate_weak_areas(
    candidate_id: str,
    db: AsyncSession,
    limit: int = 3
) -> Dict[str, Any]:
    """
    Analyzes candidate evaluation reports to extract lowest-scoring DSA metrics,
    examiner rationales, transcript evidence quotes, and improvement action items.
    """
    result = await db.execute(
        select(EvaluationReport, InterviewSession)
        .join(InterviewSession, EvaluationReport.interview_id == InterviewSession.id)
        .where(EvaluationReport.user_id == candidate_id)
        .order_by(desc(EvaluationReport.created_at))
    )
    rows = result.all()

    if not rows:
        return {
            "has_evaluations": False,
            "total_evaluations": 0,
            "weak_metrics": [],
            "citations": [],
            "formatted_synthesis": (
                "I checked your interview archives, and you have not completed an evaluated interview yet. "
                "To get a personalized breakdown of your weak areas, complete an interview in the **Interview** tab! "
                "In the meantime, I can guide you on core algorithms or design a roadmap—what would you like to start with?"
            )
        }

    parsed_reports = [_parse_report(rep, sess) for rep, sess in rows]
    total_evals = len(parsed_reports)

    # Collect metric performance across all sessions
    metric_aggregates: Dict[str, Dict[str, Any]] = {}

    for rep in parsed_reports:
        dsa_metrics = rep.get("dsa_metrics", {})
        for m_key, m_val in dsa_metrics.items():
            sc = float(m_val.get("score", 3.0))
            m_name = m_val.get("name", m_key.replace("_", " ").title())
            rationale = m_val.get("rationale", "")
            quote = m_val.get("evidence_quote", "")
            tip = m_val.get("growth_tip", "")

            if m_key not in metric_aggregates:
                metric_aggregates[m_key] = {
                    "key": m_key,
                    "name": m_name,
                    "scores": [],
                    "instances": []
                }
            metric_aggregates[m_key]["scores"].append(sc)
            metric_aggregates[m_key]["instances"].append({
                "topic": rep["topic"],
                "date": rep["date"],
                "score": sc,
                "rationale": rationale,
                "evidence_quote": quote,
                "growth_tip": tip
            })

    # Rank metrics by lowest average score
    ranked_metrics = []
    for m_key, data in metric_aggregates.items():
        avg_sc = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 4.0
        lowest_instance = min(data["instances"], key=lambda x: x["score"]) if data["instances"] else None
        ranked_metrics.append({
            "key": m_key,
            "name": data["name"],
            "avg_score": round(avg_sc, 2),
            "lowest_score": lowest_instance["score"] if lowest_instance else avg_sc,
            "lowest_instance": lowest_instance
        })

    ranked_metrics.sort(key=lambda x: (x["lowest_score"], x["avg_score"]))
    weak_metrics = ranked_metrics[:limit]

    # Collect unique improvement bullets from reports
    all_improvements = []
    for rep in parsed_reports:
        for imp in rep.get("improvements", []):
            if imp and imp not in all_improvements:
                all_improvements.append(imp)

    # Build citations
    citations = []
    for wm in weak_metrics:
        inst = wm.get("lowest_instance")
        if inst:
            citations.append({
                "topic": inst["topic"],
                "score": inst["score"],
                "date": inst["date"],
                "weak_dimension": wm["name"]
            })

    # Generate candidate-specific synthesis
    lines = [
        f"### 🔍 Diagnostic Review: Your Evaluated Weak Areas ({total_evals} Session{'s' if total_evals > 1 else ''} Analyzed)",
        "",
        "Based on your actual interview evaluations stored in your candidate scorecard, here are the specific areas where you lost points and how to fix them:",
        ""
    ]

    for idx, wm in enumerate(weak_metrics, 1):
        inst = wm.get("lowest_instance") or {}
        topic_name = inst.get("topic", "Technical DSA")
        score_val = inst.get("score", wm["lowest_score"])
        lines.append(f"#### {idx}. {wm['name']} — Evaluated Score: **{score_val:.1f}/4.0** (Topic: *{topic_name}*)")
        if inst.get("rationale"):
            lines.append(f"- **Examiner Finding**: {inst['rationale']}")
        if inst.get("evidence_quote"):
            lines.append(f"- **Transcript Evidence**: *\"{inst['evidence_quote']}\"*")
        if inst.get("growth_tip"):
            lines.append(f"- **Actionable Fix**: {inst['growth_tip']}")
        lines.append("")

    if all_improvements:
        lines.append("#### 📋 Targeted Action Items from Past Scorecards:")
        for imp in all_improvements[:4]:
            lines.append(f"- {imp}")
        lines.append("")

    lines.append("Would you like me to walk through a targeted coding drill right now to eliminate one of these bottlenecks?")

    formatted = "\n".join(lines)

    return {
        "has_evaluations": True,
        "total_evaluations": total_evals,
        "weak_metrics": weak_metrics,
        "improvements": all_improvements,
        "citations": citations[:3],
        "formatted_synthesis": formatted
    }

async def get_candidate_strengths(
    candidate_id: str,
    db: AsyncSession,
    target: str = "overall"
) -> Dict[str, Any]:
    """
    Extracts candidate strengths, top-scoring dimensions, and examiner praise quotes.
    target: 'latest' for the most recent session, or 'overall' across all history.
    """
    result = await db.execute(
        select(EvaluationReport, InterviewSession)
        .join(InterviewSession, EvaluationReport.interview_id == InterviewSession.id)
        .where(EvaluationReport.user_id == candidate_id)
        .order_by(desc(EvaluationReport.created_at))
    )
    rows = result.all()

    if not rows:
        return {
            "has_evaluations": False,
            "total_evaluations": 0,
            "strengths": [],
            "citations": [],
            "formatted_synthesis": (
                "I checked your interview scorecard, but you haven't completed an interview session yet. "
                "Once you complete an interview in the **Interview** tab, I will analyze your performance "
                "and highlight your top strengths and strong points!"
            )
        }

    parsed_reports = [_parse_report(rep, sess) for rep, sess in rows]
    total_evals = len(parsed_reports)

    selected_reports = [parsed_reports[0]] if target == "latest" else parsed_reports
    primary_rep = selected_reports[0]

    strong_metrics = []
    for rep in selected_reports:
        dsa_metrics = rep.get("dsa_metrics", {})
        for m_key, m_val in dsa_metrics.items():
            sc = float(m_val.get("score", 0.0))
            if sc >= 3.0:
                strong_metrics.append({
                    "key": m_key,
                    "name": m_val.get("name", m_key.replace("_", " ").title()),
                    "score": sc,
                    "topic": rep["topic"],
                    "date": rep["date"],
                    "rationale": m_val.get("rationale", ""),
                    "evidence_quote": m_val.get("evidence_quote", "")
                })

    strong_metrics.sort(key=lambda x: x["score"], reverse=True)

    # Collect strengths strings
    all_strengths = []
    for rep in selected_reports:
        for s in rep.get("strengths", []):
            if s and s not in all_strengths:
                all_strengths.append(s)

    citations = [{
        "topic": primary_rep["topic"],
        "score": primary_rep["overall_score"],
        "date": primary_rep["date"],
        "strengths": all_strengths[:2]
    }]

    # Build formatted synthesis
    header_title = (
        f"### 🌟 Your Strong Points in the Last Interview (*{primary_rep['topic']}*)"
        if target == "latest"
        else f"### 🌟 Your Top Evaluated Strengths Across {total_evals} Interview{'s' if total_evals > 1 else ''}"
    )

    lines = [
        header_title,
        f"- **Session Date**: {primary_rep['date']} | **Overall Score**: **{primary_rep['overall_score']:.1f}/4.0**",
        ""
    ]

    if all_strengths:
        lines.append("#### 🏆 Key Demonstrated Strengths:")
        for s in all_strengths:
            lines.append(f"- **{s}**")
        lines.append("")

    if strong_metrics:
        lines.append("#### 📈 High-Scoring Dimensions:")
        for sm in strong_metrics[:3]:
            lines.append(f"- **{sm['name']}** (**{sm['score']:.1f}/4.0** on *{sm['topic']}*)")
            if sm.get("rationale"):
                lines.append(f"  *Examiner Note*: {sm['rationale']}")
            if sm.get("evidence_quote"):
                lines.append(f"  *Transcript Proof*: *\"{sm['evidence_quote']}\"*")
        lines.append("")

    lines.append(
        "Maintaining these strengths while hardening your boundary conditions and edge cases "
        "is the quickest route to an offer. What topic would you like to practice next?"
    )

    formatted = "\n".join(lines)

    return {
        "has_evaluations": True,
        "total_evaluations": total_evals,
        "target": target,
        "primary_topic": primary_rep["topic"],
        "overall_score": primary_rep["overall_score"],
        "strengths": all_strengths,
        "strong_metrics": strong_metrics[:3],
        "citations": citations,
        "formatted_synthesis": formatted
    }

async def get_latest_interview_report(
    candidate_id: str,
    db: AsyncSession
) -> Dict[str, Any]:
    """
    Retrieves full audit of the candidate's most recent completed interview.
    """
    result = await db.execute(
        select(EvaluationReport, InterviewSession)
        .join(InterviewSession, EvaluationReport.interview_id == InterviewSession.id)
        .where(EvaluationReport.user_id == candidate_id)
        .order_by(desc(EvaluationReport.created_at))
        .limit(1)
    )
    row = result.first()

    if not row:
        return {
            "has_evaluations": False,
            "citations": [],
            "formatted_synthesis": (
                "You don't have any completed interview sessions recorded yet. "
                "Start an interview in the **Interview** tab (coached or real mode) to receive a full scorecard!"
            )
        }

    rep, sess = row
    data = _parse_report(rep, sess)

    citations = [{
        "topic": data["topic"],
        "score": data["overall_score"],
        "date": data["date"],
        "strengths": data["strengths"][:2],
        "improvements": data["improvements"][:2]
    }]

    lines = [
        f"### 📊 Debrief: Your Last Interview on **{data['topic']}**",
        f"- **Date**: {data['date']} | **Mode**: {data['interview_mode'].title()} | **Overall Score**: **{data['overall_score']:.1f}/4.0**",
        ""
    ]

    if data.get("detailed_feedback"):
        lines.append(f"**Examiner Summary**: {data['detailed_feedback']}")
        lines.append("")

    if data.get("strengths"):
        lines.append("#### ✅ Strengths:")
        for s in data["strengths"]:
            lines.append(f"- {s}")
        lines.append("")

    if data.get("improvements"):
        lines.append("#### ⚠️ Areas for Improvement:")
        for imp in data["improvements"]:
            lines.append(f"- {imp}")
        lines.append("")

    dsa_metrics = data.get("dsa_metrics", {})
    if dsa_metrics:
        lines.append("#### 📐 Rubric Breakdown:")
        for m_key, m_val in dsa_metrics.items():
            sc = m_val.get("score", 0.0)
            name = m_val.get("name", m_key.replace("_", " ").title())
            lines.append(f"- **{name}**: **{sc:.1f}/4.0** — {m_val.get('rationale', '')}")
        lines.append("")

    lines.append("Would you like to drill the areas flagged in this interview together?")
    formatted = "\n".join(lines)

    return {
        "has_evaluations": True,
        "report_data": data,
        "citations": citations,
        "formatted_synthesis": formatted
    }

async def get_metric_breakdown(
    candidate_id: str,
    metric_query: str,
    db: AsyncSession
) -> Dict[str, Any]:
    """
    Deep-dives into a specific evaluated DSA dimension (e.g. edge cases, Big-O complexity).
    """
    # Identify target metric key
    q_lower = metric_query.lower()
    target_metric_key = None
    target_metric_name = "Target Dimension"

    for m_key, aliases in METRIC_ALIASES.items():
        if any(alias in q_lower for alias in aliases):
            target_metric_key = m_key
            target_metric_name = m_key.replace("_", " ").title()
            break

    if not target_metric_key:
        target_metric_key = "edge_cases"
        target_metric_name = "Edge Case Handling"

    result = await db.execute(
        select(EvaluationReport, InterviewSession)
        .join(InterviewSession, EvaluationReport.interview_id == InterviewSession.id)
        .where(EvaluationReport.user_id == candidate_id)
        .order_by(desc(EvaluationReport.created_at))
    )
    rows = result.all()

    if not rows:
        return {
            "has_evaluations": False,
            "citations": [],
            "formatted_synthesis": (
                f"You haven't completed any interviews yet, so I don't have historical evaluation records for **{target_metric_name}**. "
                f"Complete a session in the **Interview** tab to get detailed scorecard metrics!"
            )
        }

    instances = []
    citations = []

    for rep, sess in rows:
        rep_data = _parse_report(rep, sess)
        dsa_metrics = rep_data.get("dsa_metrics", {})
        m_data = dsa_metrics.get(target_metric_key)
        if m_data:
            instances.append({
                "topic": rep_data["topic"],
                "date": rep_data["date"],
                "score": float(m_data.get("score", 0.0)),
                "rationale": m_data.get("rationale", ""),
                "evidence_quote": m_data.get("evidence_quote", ""),
                "growth_tip": m_data.get("growth_tip", "")
            })
            citations.append({
                "topic": rep_data["topic"],
                "score": float(m_data.get("score", 0.0)),
                "date": rep_data["date"]
            })

    if not instances:
        return {
            "has_evaluations": True,
            "citations": [],
            "formatted_synthesis": (
                f"In your completed interviews, **{target_metric_name}** did not have sufficient code evidence flagged for evaluation. "
                "To get evaluated on this metric, make sure to explicitly discuss constraints, test cases, and edge cases with the interviewer!"
            )
        }

    avg_score = sum(i["score"] for i in instances) / len(instances)
    latest_inst = instances[0]

    lines = [
        f"### 🔬 Metric Deep-Dive: **{target_metric_name}**",
        f"- **Historical Average**: **{avg_score:.1f}/4.0** across {len(instances)} session{'s' if len(instances) > 1 else ''}",
        f"- **Most Recent Score**: **{latest_inst['score']:.1f}/4.0** on *{latest_inst['topic']}* ({latest_inst['date']})",
        ""
    ]

    if latest_inst.get("rationale"):
        lines.append(f"**Latest Examiner Finding**: {latest_inst['rationale']}")
    if latest_inst.get("evidence_quote"):
        lines.append(f"**Transcript Quote**: *\"{latest_inst['evidence_quote']}\"*")
    if latest_inst.get("growth_tip"):
        lines.append(f"**Growth Tip**: {latest_inst['growth_tip']}")
    lines.append("")

    lines.append(f"Would you like to practice a problem where **{target_metric_name}** is the primary challenge?")
    formatted = "\n".join(lines)

    return {
        "has_evaluations": True,
        "metric_key": target_metric_key,
        "metric_name": target_metric_name,
        "average_score": avg_score,
        "instances": instances,
        "citations": citations[:2],
        "formatted_synthesis": formatted
    }

async def get_progress_and_trends(
    candidate_id: str,
    db: AsyncSession
) -> Dict[str, Any]:
    """
    Evaluates historical score progression across all completed sessions.
    """
    result = await db.execute(
        select(EvaluationReport, InterviewSession)
        .join(InterviewSession, EvaluationReport.interview_id == InterviewSession.id)
        .where(EvaluationReport.user_id == candidate_id)
        .order_by(EvaluationReport.created_at.asc())  # Chronological order
    )
    rows = result.all()

    if not rows:
        return {
            "has_evaluations": False,
            "citations": [],
            "formatted_synthesis": (
                "You don't have any completed interview records yet. Complete 2 or more interviews to unlock "
                "trajectory tracking and historical progress analysis!"
            )
        }

    reports = [_parse_report(rep, sess) for rep, sess in rows]
    total_evals = len(reports)

    if total_evals == 1:
        first = reports[0]
        return {
            "has_evaluations": True,
            "total_evaluations": 1,
            "citations": [{"topic": first["topic"], "score": first["overall_score"], "date": first["date"]}],
            "formatted_synthesis": (
                f"### 📈 Performance Baseline: 1 Completed Session\n"
                f"You currently have **1 evaluated session** on record (*{first['topic']}* on {first['date']}) with an overall score of **{first['overall_score']:.1f}/4.0**.\n\n"
                f"- **Demonstrated Strengths**: {', '.join(first['strengths']) if first['strengths'] else 'Good baseline'}\n"
                f"- **Identified Growth Areas**: {', '.join(first['improvements']) if first['improvements'] else 'Edge case testing'}\n\n"
                f"Complete a second interview in the **Interview** tab to see your progress curve and comparative delta!"
            )
        }

    first = reports[0]
    latest = reports[-1]
    score_delta = latest["overall_score"] - first["overall_score"]
    delta_str = f"+{score_delta:.1f}" if score_delta >= 0 else f"{score_delta:.1f}"

    citations = [
        {"topic": first["topic"], "score": first["overall_score"], "date": first["date"]},
        {"topic": latest["topic"], "score": latest["overall_score"], "date": latest["date"]}
    ]

    lines = [
        f"### 📈 Your Interview Progress Trajectory ({total_evals} Sessions Tracked)",
        f"- **Initial Score**: **{first['overall_score']:.1f}/4.0** on *{first['topic']}* ({first['date']})",
        f"- **Latest Score**: **{latest['overall_score']:.1f}/4.0** on *{latest['topic']}* ({latest['date']})",
        f"- **Overall Delta**: **{delta_str} points**",
        ""
    ]

    lines.append("#### 🗓️ Chronological Timeline:")
    for idx, r in enumerate(reports, 1):
        lines.append(f"{idx}. **{r['topic']}** ({r['date']}) — Score: **{r['overall_score']:.1f}/4.0**")
    lines.append("")

    lines.append("Would you like to schedule a mock session to push your average into the 3.5+ hire range?")
    formatted = "\n".join(lines)

    return {
        "has_evaluations": True,
        "total_evaluations": total_evals,
        "score_delta": score_delta,
        "timeline": reports,
        "citations": citations,
        "formatted_synthesis": formatted
    }

async def recommend_practice_problem(
    candidate_id: str,
    db: AsyncSession,
    focus_topic: Optional[str] = None
) -> Dict[str, Any]:
    """
    Cross-references candidate's weakest evaluated metric/topic with the curated question bank.
    """
    # Fetch candidate weak areas
    weak_res = await get_candidate_weak_areas(candidate_id, db, limit=1)
    weak_metric = weak_res["weak_metrics"][0]["name"] if weak_res["weak_metrics"] else "Edge Case Rigor"

    all_questions = question_loader.get_all_questions()
    if not all_questions:
        try:
            import json
            from pathlib import Path
            qpath = Path(__file__).resolve().parent.parent / "data" / "questions.json"
            if qpath.exists():
                with open(qpath, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                    from backend.services.question_loader import QuestionItem
                    all_questions = [QuestionItem(**q) for q in raw]
        except Exception as e:
            logger.warning(f"Could not load questions: {e}")

    # Pick question matching focus_topic or weakest area
    selected_q = None
    if focus_topic:
        for q in all_questions:
            if focus_topic.lower() in q.category.lower():
                selected_q = q
                break

    if not selected_q and all_questions:
        # Pick medium question
        mediums = [q for q in all_questions if q.difficulty == "medium"]
        selected_q = mediums[0] if mediums else all_questions[0]

    if not selected_q:
        return {
            "has_evaluations": weak_res["has_evaluations"],
            "citations": weak_res["citations"],
            "formatted_synthesis": "I recommend practicing Kadane's Algorithm or Rotated Array Binary Search to harden your boundary checks."
        }

    lines = [
        f"### 🎯 Tailored Practice Recommendation to Overcome **{weak_metric}**",
        "",
        f"To target the areas flagged in your evaluations, I recommend tackling this specific question:",
        "",
        f"#### **{selected_q.category}: {selected_q.difficulty.upper()}**",
        f"```text\n{selected_q.text}\n```",
        f"- **Optimal Target Complexity**: `{selected_q.optimal_complexity}`",
        ""
    ]

    if selected_q.follow_ups:
        lines.append("**Key Boundary & Follow-up Challenges**:")
        for fu in selected_q.follow_ups:
            lines.append(f"- {fu}")
        lines.append("")

    lines.append("Try outlining your approach, invariants, and edge case guards right here in chat—I'll review your solution step-by-step!")
    formatted = "\n".join(lines)

    return {
        "has_evaluations": weak_res["has_evaluations"],
        "recommended_question_id": selected_q.id,
        "category": selected_q.category,
        "difficulty": selected_q.difficulty,
        "citations": weak_res["citations"],
        "formatted_synthesis": formatted
    }
