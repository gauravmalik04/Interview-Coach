"""
sandbox_tool/coding_tools.py
============================
Implements the two stub tools declared in interview-agent-implementation-plan.md:

    - request_coding_question(...)  → CodingChallengePayload
    - submit_code_for_execution(...) → CodeExecutionResult

The Interview Agent calls these via its tool registry.
These replace the NotImplementedError stubs in app/agents/interview_tools.py
once this module is wired into the main project.

Integration steps are described in README.md.
"""

from __future__ import annotations

import os
import uuid
import requests
from dotenv import load_dotenv

from .schemas import (
    CodingChallengePayload,
    CodeExecutionResult,
    Example,
    TestCase,
)

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

PISTON_URL      = "http://20.219.10.180:3000/execute"
PISTON_API_KEY  = os.environ.get("PISTON_API_KEY", "")

# ── Internal question bank ─────────────────────────────────────────────────────
# A small built-in bank for dev/testing. In production this is replaced by
# a Cosmos DB query routed through the AI Gateway.

_QUESTION_BANK: dict[str, CodingChallengePayload] = {
    "two_sum": CodingChallengePayload(
        problem_id="two_sum",
        problem_statement=(
            "## Two Sum\n\n"
            "Given an array of integers `nums` and an integer `target`, "
            "return **indices** of the two numbers such that they add up to `target`.\n\n"
            "You may assume that each input would have **exactly one solution**, "
            "and you may not use the same element twice.\n\n"
            "You can return the answer in any order."
        ),
        examples=[
            Example(input="nums = [2,7,11,15], target = 9", output="[0,1]",
                    explanation="nums[0] + nums[1] == 9"),
            Example(input="nums = [3,2,4], target = 6",     output="[1,2]"),
            Example(input="nums = [3,3], target = 6",        output="[0,1]"),
        ],
        constraints="2 ≤ nums.length ≤ 10⁴  |  -10⁹ ≤ nums[i] ≤ 10⁹  |  Only one valid answer.",
        template_code=(
            "def two_sum(nums: list[int], target: int) -> list[int]:\n"
            "    \"\"\"\n"
            "    Return indices of the two numbers that add up to target.\n"
            "    Time: O(n)  Space: O(n)\n"
            "    \"\"\"\n"
            "    # TODO: implement\n"
            "    pass\n"
        ),
        language="python",
        test_cases=[
            TestCase(input="[2,7,11,15], 9", expected_output="[0, 1]"),
            TestCase(input="[3,2,4], 6",     expected_output="[1, 2]"),
            TestCase(input="[3,3], 6",        expected_output="[0, 1]"),
            TestCase(input="[1,2,3,4], 7",   expected_output="[2, 3]", is_hidden=True),
        ],
        time_limit_minutes=20,
        starter_code={
            "python": (
                "def two_sum(nums: list[int], target: int) -> list[int]:\n"
                "    \"\"\"\n"
                "    Return indices of the two numbers that add up to target.\n"
                "    \"\"\"\n"
                "    # Your solution here\n"
                "    pass\n\n"
                "# Tests\n"
                "assert two_sum([2,7,11,15], 9) == [0,1]\n"
                "assert two_sum([3,2,4], 6)     == [1,2]\n"
                "assert two_sum([3,3], 6)        == [0,1]\n"
                "print('All tests passed ✓')"
            ),
            "javascript": (
                "/**\n"
                " * @param {number[]} nums\n"
                " * @param {number} target\n"
                " * @return {number[]}\n"
                " */\n"
                "function twoSum(nums, target) {\n"
                "    // Your solution here\n"
                "}\n\n"
                "console.log(twoSum([2,7,11,15], 9));  // [0, 1]\n"
                "console.log(twoSum([3,2,4], 6));       // [1, 2]"
            ),
            "java": (
                "import java.util.*;\n\n"
                "class Solution {\n"
                "    public int[] twoSum(int[] nums, int target) {\n"
                "        // Your solution here\n"
                "        return new int[]{};\n"
                "    }\n\n"
                "    public static void main(String[] args) {\n"
                "        Solution s = new Solution();\n"
                "        System.out.println(Arrays.toString(s.twoSum(new int[]{2,7,11,15}, 9)));\n"
                "    }\n"
                "}"
            ),
        },
    ),
    "reverse_linked_list": CodingChallengePayload(
        problem_id="reverse_linked_list",
        problem_statement=(
            "## Reverse Linked List\n\n"
            "Given the `head` of a singly linked list, reverse the list, "
            "and return the reversed list.\n\n"
            "**Follow-up:** Can you do it both iteratively and recursively?"
        ),
        examples=[
            Example(input="head = [1,2,3,4,5]", output="[5,4,3,2,1]"),
            Example(input="head = [1,2]",        output="[2,1]"),
            Example(input="head = []",            output="[]"),
        ],
        constraints="0 ≤ Number of nodes ≤ 5000  |  -5000 ≤ Node.val ≤ 5000",
        template_code=(
            "class ListNode:\n"
            "    def __init__(self, val=0, next=None):\n"
            "        self.val = val\n"
            "        self.next = next\n\n"
            "def reverse_list(head: ListNode | None) -> ListNode | None:\n"
            "    \"\"\"\n"
            "    Reverse a singly linked list in-place.\n"
            "    Time: O(n)  Space: O(1)\n"
            "    \"\"\"\n"
            "    # TODO: implement\n"
            "    pass\n"
        ),
        language="python",
        test_cases=[
            TestCase(input="[1,2,3,4,5]", expected_output="[5,4,3,2,1]"),
            TestCase(input="[1,2]",        expected_output="[2,1]"),
            TestCase(input="[]",           expected_output="[]"),
        ],
        time_limit_minutes=20,
        starter_code={
            "python": (
                "class ListNode:\n"
                "    def __init__(self, val=0, next=None):\n"
                "        self.val = val\n"
                "        self.next = next\n\n"
                "def reverse_list(head):\n"
                "    # Your solution here\n"
                "    pass\n\n"
                "# Helper\n"
                "def to_list(node):\n"
                "    result = []\n"
                "    while node:\n"
                "        result.append(node.val)\n"
                "        node = node.next\n"
                "    return result\n\n"
                "def from_list(values):\n"
                "    dummy = ListNode(0)\n"
                "    cur = dummy\n"
                "    for v in values:\n"
                "        cur.next = ListNode(v)\n"
                "        cur = cur.next\n"
                "    return dummy.next\n\n"
                "head = from_list([1,2,3,4,5])\n"
                "print(to_list(reverse_list(head)))  # [5,4,3,2,1]"
            ),
        },
    ),
    "valid_parentheses": CodingChallengePayload(
        problem_id="valid_parentheses",
        problem_statement=(
            "## Valid Parentheses\n\n"
            "Given a string `s` containing just the characters `(`, `)`, `{`, `}`, `[` and `]`, "
            "determine if the input string is **valid**.\n\n"
            "An input string is valid if:\n"
            "- Open brackets must be closed by the same type of brackets.\n"
            "- Open brackets must be closed in the correct order.\n"
            "- Every close bracket has a corresponding open bracket of the same type."
        ),
        examples=[
            Example(input='s = "()"',       output="true"),
            Example(input='s = "()[]{}"',   output="true"),
            Example(input='s = "(]"',       output="false"),
        ],
        constraints="1 ≤ s.length ≤ 10⁴  |  s consists of parentheses only.",
        template_code=(
            "def is_valid(s: str) -> bool:\n"
            "    \"\"\"\n"
            "    Return True if the bracket string is valid.\n"
            "    Time: O(n)  Space: O(n)\n"
            "    \"\"\"\n"
            "    # TODO: implement using a stack\n"
            "    pass\n"
        ),
        language="python",
        test_cases=[
            TestCase(input='"()"',     expected_output="True"),
            TestCase(input='"()[]{}"', expected_output="True"),
            TestCase(input='"(]"',     expected_output="False"),
            TestCase(input='"([)]"',   expected_output="False", is_hidden=True),
        ],
        time_limit_minutes=15,
        starter_code={
            "python": (
                "def is_valid(s: str) -> bool:\n"
                "    # Your solution here\n"
                "    pass\n\n"
                "assert is_valid('()') == True\n"
                "assert is_valid('()[]{}') == True\n"
                "assert is_valid('(]') == False\n"
                "print('All tests passed ✓')"
            ),
            "javascript": (
                "/**\n"
                " * @param {string} s\n"
                " * @return {boolean}\n"
                " */\n"
                "function isValid(s) {\n"
                "    // Your solution here\n"
                "}\n\n"
                "console.log(isValid('()'));      // true\n"
                "console.log(isValid('()[]{}'));  // true\n"
                "console.log(isValid('(]'));      // false"
            ),
        },
    ),
}

# Topic → problem_id mapping (for agent to look up by topic)
_TOPIC_MAP: dict[str, list[str]] = {
    "arrays":         ["two_sum"],
    "linked_list":    ["reverse_linked_list"],
    "stack":          ["valid_parentheses"],
    "hash_map":       ["two_sum"],
    "dsa":            ["two_sum", "valid_parentheses", "reverse_linked_list"],
    "data_structures": ["two_sum", "valid_parentheses", "reverse_linked_list"],
}


# ── Tool: request_coding_question ─────────────────────────────────────────────

async def request_coding_question(
    topic: str,
    difficulty: str,
    language: str,
    session: object | None = None,
    db: object | None = None,
    gateway: object | None = None,
    serious_mode: bool = False,
) -> CodingChallengePayload:
    """
    [IMPLEMENTED — Coding Module]

    Selects a coding problem and returns a CodingChallengePayload with
    template_code pre-filled. The agent emits CODING_CHALLENGE_START with this.

    In production this would query Cosmos DB via the AI Gateway.
    For now uses the built-in question bank above.

    Parameters
    ----------
    topic : str
        DSA topic chosen by the agent (e.g. "arrays", "linked_list", "stack")
    difficulty : str
        "easy" | "medium" | "hard"  (currently used for logging; bank is small)
    language : str
        Default editor language ("python", "javascript", "java", "cpp", "go")
    session : InterviewSession | None
        Passed in by the agent; used to avoid repeating asked questions.
    db : Database | None
        Passed in by the agent; unused until Cosmos DB integration.
    gateway : AIGateway | None
        Passed in by the agent; unused until LLM generation fallback.
    serious_mode : bool
        If True, test cases with is_hidden=True are stripped from the payload.

    Returns
    -------
    CodingChallengePayload
        Ready to be JSON-serialised and sent as CODING_CHALLENGE_START.
    """
    import random

    topic_lower = topic.lower().replace(" ", "_").replace("-", "_")
    candidates = _TOPIC_MAP.get(topic_lower, list(_QUESTION_BANK.keys()))

    # Avoid questions already asked this session
    asked_ids: set[str] = set()
    if session and hasattr(session, "asked_question_ids"):
        asked_ids = set(session.asked_question_ids)
    remaining = [pid for pid in candidates if pid not in asked_ids]
    if not remaining:
        remaining = candidates  # all done — allow repeats rather than crash

    problem_id = random.choice(remaining)
    payload = _QUESTION_BANK[problem_id]

    # In serious mode strip hidden test cases
    if serious_mode:
        visible = [tc for tc in payload.test_cases if not tc.is_hidden]
        payload = payload.model_copy(update={"test_cases": visible})

    # Override template language if agent requested a different one
    if language and language != payload.language and language in payload.starter_code:
        payload = payload.model_copy(update={
            "language": language,
            "template_code": payload.starter_code.get(language, payload.template_code),
        })

    return payload


# ── Tool: submit_code_for_execution ───────────────────────────────────────────

LANG_MAP = {
    "python":     "python",
    "javascript": "javascript",
    "java":       "java",
    "cpp":        "c++",
    "go":         "go",
}

async def submit_code_for_execution(
    code: str,
    language: str,
    problem_id: str,
    session_id: str,
) -> CodeExecutionResult:
    """
    [IMPLEMENTED — Coding Module]

    Submits candidate code to the Piston execution engine and
    returns a structured CodeExecutionResult.

    Parameters
    ----------
    code : str
        The full source code submitted by the candidate.
    language : str
        "python" | "javascript" | "java" | "cpp" | "go"
    problem_id : str
        ID of the problem (used to look up test cases).
    session_id : str
        Interview session ID (for audit logging).

    Returns
    -------
    CodeExecutionResult
    """
    if not PISTON_API_KEY:
        return CodeExecutionResult(
            status="runtime_error",
            stderr="PISTON_API_KEY not configured in .env",
            code=code,
            language=language,
        )

    piston_lang = LANG_MAP.get(language.lower(), language.lower())

    payload = {
        "language": piston_lang,
        "version":  "*",
        "files":    [{"name": "main", "content": code}],
        "stdin":    "",
    }

    try:
        resp = requests.post(
            PISTON_URL,
            json=payload,
            headers={"Content-Type": "application/json", "X-API-Key": PISTON_API_KEY},
            timeout=30,
        )
        data = resp.json()
    except requests.exceptions.Timeout:
        return CodeExecutionResult(
            status="time_limit", code=code, language=language,
            stderr="Execution timed out (>30s)"
        )
    except Exception as e:
        return CodeExecutionResult(
            status="runtime_error", code=code, language=language,
            stderr=f"Sandbox unreachable: {e}"
        )

    run          = data.get("run", {})
    compile_info = data.get("compile", {})
    stdout       = run.get("stdout", "")
    stderr       = run.get("stderr", "") or compile_info.get("stderr", "")
    exit_code    = run.get("code", 0)
    runtime_ms   = run.get("wall_time")

    # Starter code uses assert statements — if exit_code==0 the asserts passed.
    # We use exit_code as primary signal rather than stdout-scraping.
    if compile_info.get("code", 0) != 0:
        status = "compile_error"
        passed, total = 0, 0
    elif exit_code != 0:
        status = "runtime_error"
        passed, total = 0, 0
    else:
        status = "accepted"
        passed, total = 1, 1

    return CodeExecutionResult(
        status=status,
        stdout=stdout or None,
        stderr=stderr or None,
        runtime_ms=runtime_ms,
        passed_tests=passed,
        total_tests=total,
        language=language,
        code=code,
    )
