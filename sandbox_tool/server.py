"""
sandbox_tool/server.py
======================
Flask micro-server that:
  1. Serves the coding sandbox UI  (GET /)
  2. Proxies code execution to Piston  (POST /run)
  3. Accepts a question payload from the agent  (POST /set-question)
  4. Lets the agent open the sandbox in the browser  (POST /open)

Usage — the interview agent just does:
    from sandbox_tool import SandboxTool
    sb = SandboxTool()
    sb.start()                     # start server once
    sb.open_for_question(question) # call whenever a coding question appears
"""

import os
import json
import threading
import webbrowser
import requests
from flask import Flask, request, jsonify, render_template, send_from_directory
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

PISTON_URL = "http://20.219.10.180:3000/execute"
PISTON_API_KEY = os.environ.get("PISTON_API_KEY", "")

LANG_MAP = {
    "python":     "python",
    "javascript": "javascript",
    "java":       "java",
    "cpp":        "c++",
    "go":         "go",
}

app = Flask(__name__,
            template_folder="templates",
            static_folder="static")

# Shared state — current question loaded in sandbox
_current_question = {
    "text": "",
    "language": "python",
    "starter_code": {}
}


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("sandbox.html")


@app.route("/question", methods=["GET"])
def get_question():
    """Frontend polls this to get the latest question from the agent."""
    return jsonify(_current_question)


@app.route("/set-question", methods=["POST"])
def set_question():
    """
    Called by the agent (Python) to push a question into the sandbox.
    Body (JSON):
        {
          "text": "Given an array ...",
          "language": "python",         # optional, default python
          "starter_code": {             # optional per-language starters
              "python": "def solve():\n    pass",
              "javascript": "function solve() {}"
          }
        }
    """
    global _current_question
    data = request.get_json(force=True)
    _current_question = {
        "text":         data.get("text", ""),
        "language":     data.get("language", "python"),
        "starter_code": data.get("starter_code", {})
    }
    return jsonify({"ok": True})


@app.route("/run", methods=["POST"])
def run_code():
    """
    Proxy to Piston.  Body (JSON):
        { "language": "python", "code": "print(1)", "stdin": "" }
    """
    body = request.get_json(force=True)
    lang_key  = body.get("language", "python").lower()
    piston_lang = LANG_MAP.get(lang_key, lang_key)
    code = body.get("code", "")
    stdin = body.get("stdin", "")

    if not PISTON_API_KEY:
        return jsonify({"success": False, "stdout": "",
                        "stderr": "PISTON_API_KEY not set in .env", "exit_code": 1})

    payload = {
        "language": piston_lang,
        "version": "*",
        "files": [{"name": "main", "content": code}],
        "stdin": stdin,
    }

    try:
        resp = requests.post(
            PISTON_URL,
            json=payload,
            headers={"Content-Type": "application/json", "X-API-Key": PISTON_API_KEY},
            timeout=30
        )
        data = resp.json()
        run = data.get("run", {})
        compile_info = data.get("compile", {})
        stdout = run.get("stdout", "")
        stderr = run.get("stderr", "") or compile_info.get("stderr", "")
        exit_code = run.get("code", 0)
        return jsonify({
            "success":   exit_code == 0 and not stderr,
            "stdout":    stdout,
            "stderr":    stderr,
            "exit_code": exit_code,
        })
    except requests.exceptions.Timeout:
        return jsonify({"success": False, "stdout": "",
                        "stderr": "Execution timed out (>30s)", "exit_code": 1})
    except Exception as e:
        return jsonify({"success": False, "stdout": "",
                        "stderr": f"Proxy error: {e}", "exit_code": 1})


@app.route("/open", methods=["POST"])
def open_browser():
    """Agent calls this to pop open the sandbox in the system browser."""
    port = int(os.environ.get("SANDBOX_PORT", 9000))
    webbrowser.open(f"http://localhost:{port}/")
    return jsonify({"ok": True})


def start_server(port=9000, debug=False):
    """Run the Flask server in a background daemon thread."""
    t = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=False),
        daemon=True
    )
    t.start()
    return t
