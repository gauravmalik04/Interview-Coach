"""
sandbox_tool/schemas.py
=======================
Pydantic schemas matching the contract defined in:
  docs/interview-agent-implementation-plan.md → app/agents/interview_agent_schemas.py

These are the types the Interview Agent expects when it calls
request_coding_question() or receives a CANDIDATE_CODE_RESULT event.
Copy these into your main project at: app/agents/interview_agent_schemas.py
and merge with the existing schema file there.
"""

from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


# ── Coding Challenge (request_coding_question output) ─────────────────────────

class Example(BaseModel):
    input: str
    output: str
    explanation: str | None = None


class TestCase(BaseModel):
    input: str
    expected_output: str
    is_hidden: bool = False          # hidden in Serious mode


class CodingChallengePayload(BaseModel):
    """
    Returned by request_coding_question() and emitted as
    CODING_CHALLENGE_START WebSocket event payload.
    The frontend opens the coding panel with this data.
    """
    problem_id: str
    problem_statement: str           # full markdown text shown to candidate
    examples: list[Example]
    constraints: str
    template_code: str               # agent pre-fills signature + docstring; candidate fills body
    language: str                    # default language for the editor
    test_cases: list[TestCase]       # hidden in serious mode (is_hidden=True)
    time_limit_minutes: int
    starter_code: dict[str, str]     # per-language starters  { "python": "...", "javascript": "..." }


# ── Code Execution (submit_code_for_execution output) ─────────────────────────

class CodeExecutionResult(BaseModel):
    """
    Returned by submit_code_for_execution().
    Also the shape of CANDIDATE_CODE_RESULT event the frontend sends back.
    """
    status: Literal["accepted", "wrong_answer", "time_limit", "runtime_error", "compile_error"]
    stdout: str | None = None
    stderr: str | None = None
    runtime_ms: int | None = None
    passed_tests: int = 0
    total_tests: int = 0
    language: str = "python"
    code: str = ""                   # the code the candidate submitted


# ── Agent events (subset — coding-related) ────────────────────────────────────

class AgentEvent(BaseModel):
    """
    Typed WebSocket event emitted by the engine to the frontend.
    type=CODING_CHALLENGE_START carries a CodingChallengePayload in `payload`.
    """
    type: Literal[
        "QUESTION", "FOLLOW_UP", "EVALUATION", "HINT",
        "CODING_CHALLENGE_START", "INTERVIEW_COMPLETE", "PROCESSING"
    ]
    content: str | None = None
    payload: dict | None = None      # CodingChallengePayload.model_dump() for CODING_CHALLENGE_START
    session_state: str = ""
