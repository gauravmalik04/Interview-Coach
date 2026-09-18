"""
sandbox_tool
============
Coding sandbox tool for the Live Interview Coach.

This module plugs into the Interview Agent's tool registry to implement
the two stub tools declared in docs/interview-agent-implementation-plan.md:

    • request_coding_question(topic, difficulty, language, ...) → CodingChallengePayload
    • submit_code_for_execution(code, language, problem_id, session_id) → CodeExecutionResult

It also provides SandboxTool — a convenience class that runs a local Flask
server serving the sandbox UI and exposes the question to the browser.

See README.md for integration instructions.
"""

from .schemas import (
    CodingChallengePayload,
    CodeExecutionResult,
    AgentEvent,
    Example,
    TestCase,
)
from .coding_tools import request_coding_question, submit_code_for_execution
from .server import app as sandbox_app, start_server


class SandboxTool:
    """
    Convenience wrapper: starts the sandbox UI server and exposes
    request_coding_question / submit_code_for_execution as methods.

    Typical agent usage:
        sb = SandboxTool(port=9000)
        sb.start()

        payload = await sb.request_coding_question(
            topic="arrays", difficulty="medium", language="python"
        )
        # agent emits CODING_CHALLENGE_START with payload.model_dump()
        # ... candidate writes code ...
        result = await sb.submit_code_for_execution(
            code=candidate_code, language="python",
            problem_id=payload.problem_id, session_id=session_id
        )
    """

    def __init__(self, port: int = 9000, auto_open: bool = True):
        import os
        self.port      = port
        self.auto_open = auto_open
        self._started  = False
        self._base     = f"http://localhost:{port}"
        os.environ["SANDBOX_PORT"] = str(port)

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def start(self):
        """Start the sandbox UI server in a background thread."""
        if self._started:
            return
        import time, requests as req
        start_server(port=self.port)
        for _ in range(20):
            try:
                req.get(self._base + "/question", timeout=1)
                break
            except Exception:
                time.sleep(0.3)
        self._started = True
        print(f"[SandboxTool] UI ready at {self._base}")

    def get_url(self) -> str:
        return self._base + "/"

    def open_for_question(
        self,
        question_text=None,
        language: str = "python",
        starter_code=None,
        auto_open: bool = None,
        **kwargs,
    ):
        """
        Push a question to the sandbox UI and open it in the browser.

        Supports:
            sb.open_for_question(question_text="...", language="python", starter_code={...})
            sb.open_for_question(coding_challenge_payload)
            sb.open_for_question({"text": "...", "language": "...", "starter_code": ...})
        """
        import requests as req
        import webbrowser

        if not self._started:
            self.start()

        if hasattr(question_text, "problem_statement"):
            text = question_text.problem_statement
            lang = getattr(question_text, "language", language)
            starter = getattr(question_text, "starter_code", starter_code) or {}
        elif isinstance(question_text, dict):
            text = question_text.get("text") or question_text.get("problem_statement", "")
            lang = question_text.get("language", language)
            starter = question_text.get("starter_code", starter_code) or {}
        else:
            text = str(question_text or "")
            lang = language
            starter = starter_code or {}

        if isinstance(starter, str):
            starter = {lang: starter}

        body = {
            "text": text,
            "language": lang,
            "starter_code": starter,
        }

        try:
            req.post(self._base + "/set-question", json=body, timeout=5)
        except Exception as e:
            print(f"[SandboxTool] Could not push question to UI: {e}")

        should_open = self.auto_open if auto_open is None else auto_open
        if should_open:
            webbrowser.open(self._base + "/")

    # ── Tool wrappers (async) ──────────────────────────────────────────────

    async def request_coding_question(
        self,
        topic: str,
        difficulty: str = "medium",
        language: str = "python",
        session=None,
        db=None,
        gateway=None,
        serious_mode: bool = False,
        push_to_browser: bool = True,
    ) -> CodingChallengePayload:
        """
        Select a coding question and (optionally) push it to the sandbox UI.

        Parameters
        ----------
        push_to_browser : bool
            If True and server is started, send the question to the live UI
            so the candidate sees it immediately. Set False if you only want
            the payload without showing the UI.
        """
        payload = await request_coding_question(
            topic=topic, difficulty=difficulty, language=language,
            session=session, db=db, gateway=gateway, serious_mode=serious_mode,
        )

        if push_to_browser and self._started:
            import requests as req
            import webbrowser
            body = {
                "text":         payload.problem_statement,
                "language":     payload.language,
                "starter_code": payload.starter_code,
            }
            try:
                req.post(self._base + "/set-question", json=body, timeout=5)
                if self.auto_open:
                    webbrowser.open(self._base + "/")
            except Exception as e:
                print(f"[SandboxTool] Could not push question to UI: {e}")

        return payload

    async def submit_code_for_execution(
        self,
        code: str,
        language: str,
        problem_id: str,
        session_id: str,
    ) -> CodeExecutionResult:
        """Submit code to Piston and return structured result."""
        return await submit_code_for_execution(
            code=code, language=language,
            problem_id=problem_id, session_id=session_id,
        )


__all__ = [
    "SandboxTool",
    "request_coding_question",
    "submit_code_for_execution",
    "CodingChallengePayload",
    "CodeExecutionResult",
    "AgentEvent",
    "Example",
    "TestCase",
]
