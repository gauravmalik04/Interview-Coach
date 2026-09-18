"""
example_agent.py
================
Example: how the interview agent calls SandboxTool during a live session.

Run this file to test the sandbox end-to-end:
    conda activate aiml
    python sandbox_tool/example_agent.py
"""

import time
from sandbox_tool import SandboxTool

# 1. Create the tool (once per session)
sb = SandboxTool(port=9000, auto_open=True)

# 2. Start the server (only needs to happen once)
sb.start()

print("Sandbox server started at", sb.get_url())
print("Opening browser...")

# 3. Simulate the agent presenting a DSA coding question
sb.open_for_question(
    question_text=(
        "Two Sum\n\n"
        "Given an array of integers nums and an integer target, return indices of "
        "the two numbers such that they add up to target.\n\n"
        "You may assume that each input would have exactly one solution, "
        "and you may not use the same element twice.\n\n"
        "Example:\n"
        "  Input:  nums = [2, 7, 11, 15], target = 9\n"
        "  Output: [0, 1]   # because nums[0] + nums[1] == 9"
    ),
    language="python",
    starter_code={
        "python": (
            "def two_sum(nums, target):\n"
            "    # Your solution here\n"
            "    pass\n\n"
            "# Tests\n"
            "assert two_sum([2, 7, 11, 15], 9) == [0, 1]\n"
            "assert two_sum([3, 2, 4], 6) == [1, 2]\n"
            "print('All tests passed ✓')"
        ),
        "javascript": (
            "function twoSum(nums, target) {\n"
            "  // Your solution here\n"
            "}\n\n"
            "console.log(twoSum([2, 7, 11, 15], 9));  // [0, 1]"
        ),
    }
)

print("\nSandbox is open in your browser.")
print("Candidate can now write code, run it, and submit.")
print("Press Ctrl+C to stop.\n")

# Keep alive so Flask thread runs
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nShutting down sandbox.")
