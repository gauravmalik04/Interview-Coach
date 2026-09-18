# sandbox_tool — Coding Sandbox for Live Interview Coach

A plug-and-play coding sandbox module that integrates with the Interview Agent
as described in `docs/interview-agent-implementation-plan.md`.

It implements the two stub tools the agent plan declares:

| Tool | Status |
|---|---|
| `request_coding_question(topic, difficulty, language, ...)` | ✅ Implemented |
| `submit_code_for_execution(code, language, problem_id, session_id)` | ✅ Implemented |

---

## Files to Copy Into the Main Project

Copy the entire `sandbox_tool/` directory into your main project root:

```
your-main-project/
├── sandbox_tool/              ← copy this whole folder
│   ├── __init__.py            ← SandboxTool class + public API
│   ├── schemas.py             ← Pydantic types (CodingChallengePayload etc.)
│   ├── coding_tools.py        ← request_coding_question + submit_code_for_execution
│   ├── server.py              ← Flask UI server (background thread)
│   ├── templates/
│   │   └── sandbox.html       ← Sandbox UI (served by Flask)
│   └── static/
│       ├── sandbox.js         ← Editor logic, polling, run/submit
│       └── sandbox.css        ← Styles
├── .env                       ← Must contain PISTON_API_KEY
└── ...
```

### Schema merge (important)

The types in `sandbox_tool/schemas.py` must also be added to your main project's
schema file at `app/agents/interview_agent_schemas.py`. Add these classes:

- `CodingChallengePayload`
- `CodeExecutionResult`
- `Example`
- `TestCase`

---

## Installing Dependencies

```bash
conda activate aiml
pip install flask requests pydantic python-dotenv
```

---

## How the Interview Agent Connects

### Step 1 — In `app/agents/interview_tools.py`

Replace the two `raise NotImplementedError` stubs with real imports:

```python
# BEFORE (stub):
async def request_coding_question(...) -> CodingChallengePayload:
    raise NotImplementedError("Coding sandbox tool not yet implemented.")

async def submit_code_for_execution(...) -> CodeExecutionResult:
    raise NotImplementedError("Code execution tool not yet implemented.")

# AFTER (wired up):
from sandbox_tool.coding_tools import (
    request_coding_question,
    submit_code_for_execution,
)
```

### Step 2 — In `app/agents/interview_agent.py`

Enable the tools in `_register_tools()` by setting `is_available=True`:

```python
def _register_tools(self) -> dict[str, Tool]:
    return {
        "get_next_question":         Tool(fn=get_next_question,         is_available=True),
        "evaluate_answer":           Tool(fn=evaluate_answer,           is_available=True),
        "get_performance_summary":   Tool(fn=get_performance_summary,   is_available=True),
        "generate_interview_report": Tool(fn=generate_interview_report, is_available=True),

        # ✅ Now available:
        "request_coding_question":   Tool(fn=request_coding_question,   is_available=True),
        "submit_code_for_execution": Tool(fn=submit_code_for_execution, is_available=True),
    }
```

### Step 3 — Start the sandbox UI server (once per session)

In your WebSocket session setup code (`app/api/v1/ws.py` or `engine.py`):

```python
from sandbox_tool import SandboxTool

# Create once per session
sandbox = SandboxTool(port=9000, auto_open=True)
sandbox.start()
```

### Step 4 — When the agent emits `CODING_CHALLENGE_START`

In your `engine.py` where you handle `AgentDecision`:

```python
from sandbox_tool import SandboxTool

if decision.action == "request_coding_challenge":
    payload: CodingChallengePayload = await sandbox.request_coding_question(
        topic=decision.topic,
        difficulty=session.difficulty,
        language="python",
        session=session,
        db=db,
        gateway=gateway,
        serious_mode=(session.mode == "serious"),
        push_to_browser=True,      # opens the sandbox in the candidate's browser
    )
    # Emit WebSocket event to frontend
    event = AgentEvent(
        type="CODING_CHALLENGE_START",
        content=f"I'd like you to solve a coding problem. The sandbox is now open.",
        payload=payload.model_dump(),
        session_state="WAITING_FOR_CODE",
    )
    await ws.send_json(event.model_dump())
```

### Step 5 — When candidate submits code (`CANDIDATE_CODE_RESULT`)

In your WebSocket handler for incoming `CANDIDATE_CODE_RESULT` events:

```python
from sandbox_tool import SandboxTool

# Event from frontend: { type: "CANDIDATE_CODE_RESULT", code, language, output }
async def on_code_result(ws_event: dict, session, sandbox: SandboxTool):
    result: CodeExecutionResult = await sandbox.submit_code_for_execution(
        code=ws_event["code"],
        language=ws_event["language"],
        problem_id=session.current_problem_id,
        session_id=session.session_id,
    )
    # Route to agent
    agent_event = await agent.on_code_result(result)
    await ws.send_json(agent_event.model_dump())
```

---

## Question Bank

Three built-in problems are included for development/testing:

| Problem ID | Topic | Difficulty |
|---|---|---|
| `two_sum` | Arrays / Hash Map | Medium |
| `reverse_linked_list` | Linked List | Easy |
| `valid_parentheses` | Stack | Easy |

### Adding more problems

In `coding_tools.py`, add an entry to `_QUESTION_BANK` and `_TOPIC_MAP`:

```python
_QUESTION_BANK["my_problem"] = CodingChallengePayload(
    problem_id="my_problem",
    problem_statement="...",
    examples=[Example(input="...", output="...")],
    constraints="...",
    template_code="def solve():\n    pass\n",
    language="python",
    test_cases=[TestCase(input="...", expected_output="...")],
    time_limit_minutes=20,
    starter_code={"python": "def solve():\n    # your code\n    pass\n"},
)

_TOPIC_MAP["my_topic"] = ["my_problem"]
```

---

## Standalone Testing

Run this to test the sandbox independently (without the main project):

```bash
conda activate aiml
cd /path/to/Live\ Interview\ Coach\ copy
python -m sandbox_tool.example_agent
```

This starts the server on `http://localhost:9000`, pushes a Two Sum question,
and opens it in your browser. You can write code, click Run, and see output.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `PISTON_API_KEY` | ✅ Yes | API key for your Piston execution server |

Set in `.env` at the project root:

```
PISTON_API_KEY=your_key_here
```

---

## API Reference

### `SandboxTool(port=9000, auto_open=True)`

| Method | Returns | Description |
|---|---|---|
| `start()` | `None` | Start Flask UI server in background thread |
| `get_url()` | `str` | URL to the sandbox UI (e.g. for embedding in iframe) |
| `await request_coding_question(topic, difficulty, language, ...)` | `CodingChallengePayload` | Select a problem and push to sandbox UI |
| `await submit_code_for_execution(code, language, problem_id, session_id)` | `CodeExecutionResult` | Execute code via Piston and return results |

### `request_coding_question(...)` (standalone async function)

```python
from sandbox_tool.coding_tools import request_coding_question

payload = await request_coding_question(
    topic="arrays",         # maps to problem bank
    difficulty="medium",    # for logging; bank is small
    language="python",      # default editor language
    session=None,           # InterviewSession (avoids repeating questions)
    db=None,                # Cosmos DB (future)
    gateway=None,           # AI Gateway (future LLM fallback)
    serious_mode=False,     # strips hidden test cases if True
)
```

### `submit_code_for_execution(...)` (standalone async function)

```python
from sandbox_tool.coding_tools import submit_code_for_execution

result = await submit_code_for_execution(
    code="def two_sum(nums, target): ...",
    language="python",
    problem_id="two_sum",
    session_id="sess_abc123",
)
# result.status: "accepted" | "wrong_answer" | "runtime_error" | "compile_error" | "time_limit"
# result.stdout, result.stderr, result.passed_tests, result.total_tests
```

### Schemas

```python
from sandbox_tool import CodingChallengePayload, CodeExecutionResult, AgentEvent

# Emit CODING_CHALLENGE_START to frontend:
event = AgentEvent(
    type="CODING_CHALLENGE_START",
    content="Open the sandbox and solve this problem.",
    payload=payload.model_dump(),
    session_state="WAITING_FOR_CODE",
)
```

---

## Sandbox UI Endpoints (Flask)

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Serve sandbox HTML |
| `GET` | `/question` | Get current question (polled by browser every 1.5s) |
| `POST` | `/set-question` | Push a question from agent → browser |
| `POST` | `/run` | Execute code via Piston, return stdout/stderr |
| `POST` | `/open` | Open sandbox in system browser |

---

## Coding Challenge Flow

```
Agent calls request_coding_question(topic="arrays", difficulty="medium")
    ↓
sandbox_tool selects "two_sum" from question bank
    ↓
Returns CodingChallengePayload with template_code pre-filled
    ↓
Engine emits CODING_CHALLENGE_START WebSocket event
    ↓
Frontend opens sandbox panel — question + starter code loaded
    ↓
Candidate writes code → clicks Run → output shown in console
    ↓
Candidate clicks Submit → browser dispatches sandbox:submit event
    ↓
Frontend sends CANDIDATE_CODE_RESULT to WebSocket
    ↓
Engine calls submit_code_for_execution(code, language, problem_id, session_id)
    ↓
Returns CodeExecutionResult { status, stdout, stderr, passed_tests, total_tests }
    ↓
Agent receives result via on_code_result(), evaluates, decides next action
```
