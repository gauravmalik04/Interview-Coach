/**
 * sandbox.js
 * Coding Sandbox — browser-side logic.
 * Polls /question, mounts CodeMirror, runs code via /run, handles submit.
 */

const PROXY = '';           // same origin — Flask serves both UI and /run
const POLL_MS = 1500;       // how often to check for new questions from the agent

const LANG_MODE = {
  python:     'python',
  javascript: 'javascript',
  java:       'text/x-java',
  cpp:        'text/x-c++src',
  go:         'text/x-go',
};

const DEFAULT_STARTER = {
  python:     'def solve():\n    # Write your solution here\n    pass\n\nprint(solve())',
  javascript: 'function solve() {\n  // Write your solution here\n}\n\nconsole.log(solve());',
  java:       'public class Main {\n    public static void main(String[] args) {\n        System.out.println(solve());\n    }\n    static int solve() {\n        return 0;\n    }\n}',
  cpp:        '#include <iostream>\nusing namespace std;\n\nint solve() {\n    return 0;\n}\n\nint main() {\n    cout << solve() << endl;\n    return 0;\n}',
  go:         'package main\nimport "fmt"\n\nfunc solve() int {\n    return 0\n}\n\nfunc main() {\n    fmt.Println(solve())\n}',
};

// ── State ─────────────────────────────────────────────────────────────────────
let editor = null;
let currentLang = 'python';
let currentQuestion = null;
let starterCodeMap = {};

// ── DOM refs ──────────────────────────────────────────────────────────────────
const panelEl       = document.getElementById('sandbox-panel');
const overlayEl     = document.getElementById('sandbox-overlay');
const closeBtn      = document.getElementById('sb-close');
const langSelect    = document.getElementById('sb-lang-select');
const questionText  = document.getElementById('sb-question-text');
const runBtn        = document.getElementById('sb-run');
const submitBtn     = document.getElementById('sb-submit');
const resetBtn      = document.getElementById('sb-reset');
const statusEl      = document.getElementById('sb-status');
const consoleOut    = document.getElementById('sb-console-output');
const editorHost    = document.getElementById('sb-editor-host');

// ── Init CodeMirror ───────────────────────────────────────────────────────────
function mountEditor(code, lang) {
  if (editor) {
    editor.setValue(code);
    editor.setOption('mode', LANG_MODE[lang] || 'python');
    editor.refresh();
    return;
  }
  editor = CodeMirror(editorHost, {
    value:           code,
    mode:            LANG_MODE[lang] || 'python',
    theme:           'material-ocean',
    lineNumbers:     true,
    indentUnit:      4,
    tabSize:         4,
    autoCloseBrackets: true,
    lineWrapping:    false,
    styleActiveLine: true,
  });
}

// ── Open / close panel ────────────────────────────────────────────────────────
function openPanel() {
  panelEl.classList.add('active');
  overlayEl.classList.add('active');
  if (editor) setTimeout(() => editor.refresh(), 320);
}
function closePanel() {
  panelEl.classList.remove('active');
  overlayEl.classList.remove('active');
}

closeBtn.addEventListener('click', closePanel);
overlayEl.addEventListener('click', closePanel);

// ── Language switch ────────────────────────────────────────────────────────────
langSelect.addEventListener('change', () => {
  currentLang = langSelect.value;
  const code = starterCodeMap[currentLang] || DEFAULT_STARTER[currentLang] || '';
  mountEditor(code, currentLang);
});

// ── Poll agent for new question ────────────────────────────────────────────────
async function pollQuestion() {
  try {
    const resp = await fetch(PROXY + '/question');
    const data = await resp.json();

    // Only update if something changed
    if (data.text && data.text !== (currentQuestion && currentQuestion.text)) {
      currentQuestion = data;
      starterCodeMap  = data.starter_code || {};
      currentLang     = data.language || 'python';

      // Update question text
      questionText.textContent = data.text;

      // Update language selector
      langSelect.value = currentLang;

      // Mount editor with starter code
      const code = starterCodeMap[currentLang] || DEFAULT_STARTER[currentLang] || '';
      mountEditor(code, currentLang);

      // Auto-open the panel
      openPanel();

      setStatus('Question loaded ✓', '#a6e3a1');
    }
  } catch (e) {
    // silently ignore — server might be warming up
  }
}

// Kick off on page load + then every POLL_MS
document.addEventListener('DOMContentLoaded', () => {
  // Mount a blank editor immediately so CodeMirror is ready
  mountEditor(DEFAULT_STARTER.python, 'python');
  openPanel();   // open on load when used standalone
  pollQuestion();
  setInterval(pollQuestion, POLL_MS);
});

// ── Run code ───────────────────────────────────────────────────────────────────
runBtn.addEventListener('click', async () => {
  const code = editor ? editor.getValue() : '';
  if (!code.trim()) { setConsole('Write some code first!', 'info'); return; }

  runBtn.disabled = true;
  setStatus('Running…', '#89dceb');
  setConsole('Running…', 'info');

  try {
    const resp = await fetch(PROXY + '/run', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ language: currentLang, code, stdin: '' }),
    });
    const result = await resp.json();

    if (result.stderr) {
      setConsole(result.stderr, 'error');
      setStatus('Error ✗', '#f38ba8');
    } else if (result.stdout) {
      setConsole(result.stdout, 'success');
      setStatus('Done ✓', '#a6e3a1');
    } else {
      setConsole('Process exited with no output.', 'info');
      setStatus('Done ✓', '#a6e3a1');
    }
  } catch (err) {
    setConsole(`Failed to reach sandbox server: ${err.message}`, 'error');
    setStatus('Error ✗', '#f38ba8');
  } finally {
    runBtn.disabled = false;
  }
});

// ── Submit ─────────────────────────────────────────────────────────────────────
submitBtn.addEventListener('click', () => {
  const code   = editor ? editor.getValue() : '';
  const output = consoleOut.textContent;
  // Emit a custom event — the parent interview app can listen to this
  // if the sandbox is embedded in an iframe or same-page context.
  window.dispatchEvent(new CustomEvent('sandbox:submit', {
    detail: { code, language: currentLang, output }
  }));
  setStatus('Submitted ✓', '#cba6f7');
  setConsole(`Code submitted (${currentLang}).\n\n${output}`, 'success');
});

// ── Reset ──────────────────────────────────────────────────────────────────────
resetBtn.addEventListener('click', () => {
  const code = starterCodeMap[currentLang] || DEFAULT_STARTER[currentLang] || '';
  if (editor) editor.setValue(code);
  setConsole('Editor reset to starter code.', 'info');
  setStatus('', '');
});

// ── Helpers ────────────────────────────────────────────────────────────────────
function setConsole(text, type) {
  consoleOut.textContent = text;
  consoleOut.className   = type;   // 'success' | 'error' | 'info'
}
function setStatus(text, color) {
  statusEl.textContent = text;
  statusEl.style.color = color;
}
