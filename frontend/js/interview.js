/**
 * AI Interview Platform — Real-Time Interview Client
 * Manages WebSocket communication, fallback HTTP endpoints, live timer,
 * conversational rendering, and the candidate workbench.
 */

let currentSessionId = null;
let currentPhase = 'intro';
let currentSessionMode = 'real';
let currentSessionStatus = 'active';
let ws = null;
let pingInterval = null;
let timerInterval = null;
let sessionSeconds = 0;
let sessionStartMs = 0;
let isWebSocketActive = false;
let isScratchpadOpen = false;

function parseUtcDate(str) {
  if (!str) return null;
  const s = (!str.endsWith('Z') && !str.includes('+')) ? str + 'Z' : str;
  const d = new Date(s);
  return isNaN(d.getTime()) ? null : d;
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', async () => {
  // Ensure scratchpad panel starts collapsed by default
  toggleScratchpad(false);

  const urlParams = new URLSearchParams(window.location.search);
  currentSessionId = urlParams.get('session_id');

  if (!currentSessionId) {
    try {
      const activeRes = await window.api.get('/sessions/active');
      if (activeRes.ok) {
        const activeData = await activeRes.json();
        if (activeData && activeData.has_active && activeData.session_id) {
          window.location.replace(`/interview?session_id=${activeData.session_id}`);
          return;
        }
      }
    } catch (e) {
      console.error('Active session check failed:', e);
    }
    window.api.showToast('No active interview found. Redirecting to dashboard...', 'info');
    setTimeout(() => { window.location.href = '/dashboard'; }, 1000);
    return;
  }

  if (!window.api.isAuthenticated()) {
    window.api.showToast('Please log in to enter the interview room.', 'error');
    setTimeout(() => { window.location.href = '/'; }, 1000);
    return;
  }

  // Setup input listeners
  const textarea = document.getElementById('candidate-input');
  if (textarea) {
    textarea.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        submitReply(e);
      }
    });
  }

  const scratchpad = document.getElementById('code-scratchpad');
  if (scratchpad) {
    scratchpad.addEventListener('input', updateCharCount);
  }

  // Fetch initial session state
  await loadSessionData();

  // Start live session timer
  startTimer();

  // Establish WebSocket connection
  connectWebSocket();
});

let currentSessionBoilerplate = '';
let currentSessionLanguage = 'python';

// Load session details and prior transcript
async function loadSessionData() {
  try {
    const res = await window.api.get(`/sessions/${currentSessionId}`);
    if (res.ok) {
      const data = await res.json();
      currentSessionMode = data.interview_mode || 'real';
      currentSessionStatus = data.status || 'active';

      // Initialize continuous uninterrupted timer from started_at
      if (data.started_at) {
        const startObj = parseUtcDate(data.started_at);
        if (startObj) {
          sessionStartMs = startObj.getTime();
        }
      }

      if (currentSessionStatus === 'completed' && data.ended_at && sessionStartMs > 0) {
        const endObj = parseUtcDate(data.ended_at);
        const endMs = endObj ? endObj.getTime() : Date.now();
        sessionSeconds = Math.max(0, Math.floor((endMs - sessionStartMs) / 1000));
      } else if (sessionStartMs > 0) {
        // Continuous uninterrupted timer: never stops even when resuming!
        sessionSeconds = Math.max(0, Math.floor((Date.now() - sessionStartMs) / 1000));
      } else if (typeof data.elapsed_seconds === 'number' && data.elapsed_seconds > 0) {
        sessionSeconds = data.elapsed_seconds;
      }

      updateTimerDisplay();

      document.getElementById('interview-topic-badge').textContent = data.topic || 'Technical Interview';
      updatePhase(data.current_phase || 'intro');

      // Update mode badge
      const modeBadge = document.getElementById('interview-mode-badge');
      if (modeBadge) {
        if (data.interview_mode === 'coached') {
          modeBadge.className = 'mode-badge-coached';
          modeBadge.innerHTML = '🎓 Coached Interview';
        } else {
          modeBadge.className = 'mode-badge-real';
          modeBadge.innerHTML = '⚡ Real Interview';
        }
      }

      // Update preferred language and boilerplate
      currentSessionLanguage = data.language || 'python';
      currentSessionBoilerplate = data.boilerplate_code || '';
      updateLanguageDisplay(currentSessionLanguage);

      const pad = document.getElementById('code-scratchpad');
      if (pad && !pad.value.trim() && currentSessionBoilerplate) {
        pad.value = currentSessionBoilerplate;
        updateCharCount();
      }

      if (data.status === 'completed') {
        showCompleteModal(data.id);
      }

      if (data.transcript && data.transcript.length > 0) {
        renderTranscript(data.transcript);
      }
    } else {
      window.api.showToast('Unable to load session data.', 'error');
    }
  } catch (err) {
    console.error('Error loading session data:', err);
  }
}

// Connect to real-time WebSocket
function connectWebSocket() {
  const token = window.api.getAccessToken();
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws/interview/${currentSessionId}?token=${encodeURIComponent(token || '')}`;

  updateConnectionStatus('connecting');

  try {
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      isWebSocketActive = true;
      updateConnectionStatus('connected');

      // Heartbeat ping every 25 seconds
      clearInterval(pingInterval);
      pingInterval = setInterval(() => {
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping', elapsed_seconds: sessionSeconds }));
        }
      }, 25000);
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        handleWebSocketMessage(msg);
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };

    ws.onclose = () => {
      isWebSocketActive = false;
      clearInterval(pingInterval);
      updateConnectionStatus('disconnected');
    };

    ws.onerror = (err) => {
      console.warn('WebSocket connection error, falling back to HTTP:', err);
      isWebSocketActive = false;
      updateConnectionStatus('fallback');
    };
  } catch (err) {
    console.error('WebSocket initialization error:', err);
    isWebSocketActive = false;
    updateConnectionStatus('fallback');
  }
}

// Handle messages received over WebSocket
function handleWebSocketMessage(msg) {
  hideTypingIndicator();

  if (msg.type === 'session_init') {
    if (msg.started_at) {
      const startObj = parseUtcDate(msg.started_at);
      if (startObj) {
        sessionStartMs = startObj.getTime();
      }
    }
    if (currentSessionStatus === 'completed' && msg.ended_at && sessionStartMs > 0) {
      const endObj = parseUtcDate(msg.ended_at);
      const endMs = endObj ? endObj.getTime() : Date.now();
      sessionSeconds = Math.max(0, Math.floor((endMs - sessionStartMs) / 1000));
    } else if (sessionStartMs > 0) {
      sessionSeconds = Math.max(0, Math.floor((Date.now() - sessionStartMs) / 1000));
    } else if (typeof msg.elapsed_seconds === 'number' && msg.elapsed_seconds > sessionSeconds) {
      sessionSeconds = msg.elapsed_seconds;
    }
    updateTimerDisplay();
    if (msg.topic) {
      document.getElementById('interview-topic-badge').textContent = msg.topic;
    }
    if (msg.phase) {
      updatePhase(msg.phase);
    }
    if (msg.transcript && msg.transcript.length > 0) {
      renderTranscript(msg.transcript);
    }
  } else if (msg.type === 'agent_message') {
    appendMessage('ai', msg.content, msg.timestamp);
    if (msg.phase) {
      updatePhase(msg.phase);
    }
    if (msg.boilerplate_code) {
      handleNewBoilerplate(msg.boilerplate_code);
    }
  } else if (msg.type === 'interview_complete') {
    updatePhase('done');
    showCompleteModal(msg.session_id || currentSessionId);
  } else if (msg.type === 'error') {
    window.api.showToast(msg.message || 'An error occurred.', 'error');
  }
}

function handleNewBoilerplate(newBoilerplate) {
  if (!newBoilerplate) return;
  currentSessionBoilerplate = newBoilerplate;
  const pad = document.getElementById('code-scratchpad');
  if (pad) {
    const val = pad.value.trim();
    // Populate if scratchpad is empty or has intro placeholder
    if (!val || val.includes('When a technical problem') || val.includes('When a technical question') || (val.length < 120 && (val.startsWith('#') || val.startsWith('//')))) {
      pad.value = newBoilerplate;
      updateCharCount();
    }
  }
}

// Submit candidate response
async function submitReply(event) {
  if (event) event.preventDefault();

  const inputEl = document.getElementById('candidate-input');
  const btn = document.getElementById('btn-submit-reply');
  let content = inputEl.value.trim();

  if (!content) return;

  // Check if code scratchpad should be attached
  const attachCode = document.getElementById('check-attach-code').checked;
  const scratchpadContent = document.getElementById('code-scratchpad').value.trim();
  const lang = document.getElementById('editor-lang').value;

  if (attachCode && scratchpadContent) {
    content += `\n\n\`\`\`${lang}\n${scratchpadContent}\n\`\`\``;
  }

  // Clear input
  inputEl.value = '';
  inputEl.style.height = 'auto';

  // Append candidate message immediately
  appendMessage('candidate', content, new Date().toISOString());
  showTypingIndicator();

  btn.disabled = true;

  try {
    if (isWebSocketActive && ws && ws.readyState === WebSocket.OPEN) {
      // Send via WebSocket
      ws.send(JSON.stringify({
        type: 'candidate_reply',
        content: content
      }));
    } else {
      // Fallback via HTTP POST
      const res = await window.api.post(`/sessions/${currentSessionId}/reply`, { content });
      const data = await res.json();
      hideTypingIndicator();

      if (res.ok) {
        appendMessage('ai', data.ai_reply, data.timestamp);
        updatePhase(data.phase);
        if (data.boilerplate_code) {
          handleNewBoilerplate(data.boilerplate_code);
        }
        if (data.is_complete) {
          showCompleteModal(currentSessionId);
        }
      } else {
        window.api.showToast(data.detail || 'Failed to send response.', 'error');
      }
    }
  } catch (err) {
    hideTypingIndicator();
    window.api.showToast('Network error submitting response.', 'error');
    console.error('Error submitting response:', err);
  } finally {
    btn.disabled = false;
  }
}

// Render full transcript history
function renderTranscript(transcript) {
  const container = document.getElementById('chat-messages');
  container.innerHTML = '';

  let lastPhase = null;
  transcript.forEach(msg => {
    appendMessage(msg.role, msg.content, msg.timestamp);
  });
}

// Append single message to chat feed
function appendMessage(role, content, timestamp) {
  const container = document.getElementById('chat-messages');
  const isAI = role === 'ai';

  const item = document.createElement('div');
  item.className = `message-item ${isAI ? 'ai-message' : 'candidate-message'}`;

  const timeStr = timestamp ? formatTime(timestamp) : 'Just now';
  const senderName = isAI ? 'AI Interviewer' : 'You (Candidate)';
  const avatarIcon = isAI ? '🤖' : '👤';
  const avatarClass = isAI ? 'ai-avatar-small' : 'candidate-avatar';

  item.innerHTML = `
    <div class="avatar ${avatarClass}">${avatarIcon}</div>
    <div class="message-bubble">
      <div class="message-meta">
        <span class="message-sender">${senderName}</span>
        <span class="message-time">${timeStr}</span>
      </div>
      <div class="message-text">${formatMessageContent(content)}</div>
    </div>
  `;

  container.appendChild(item);
  scrollToBottom();
}

// Configure marked if available
if (typeof marked !== 'undefined') {
  try {
    marked.setOptions({
      gfm: true,
      breaks: true,
      pedantic: false,
    });
  } catch (e) {
    console.warn('Could not set marked options:', e);
  }
}

// Format message text with full markdown rendering (headers, code blocks, lists, bold/italic, tables)
function formatMessageContent(raw) {
  if (!raw) return '';

  if (typeof marked !== 'undefined' && typeof marked.parse === 'function') {
    try {
      let html = marked.parse(raw);
      // Ensure target="_blank" on links for safe navigation
      html = html.replace(/<a\s+(?:[^>]*?\s+)?href="([^"]*)"([^>]*)>/gi, '<a href="$1" target="_blank" rel="noopener noreferrer"$2>');
      return html;
    } catch (err) {
      console.warn('Marked parse error, using fallback:', err);
    }
  }

  return renderFallbackMarkdown(raw);
}

function renderFallbackMarkdown(raw) {
  let text = escapeHtml(raw);

  // Headers (### Header, ## Header, # Header)
  text = text.replace(/^### (.*$)/gim, '<h3 class="message-h3">$1</h3>');
  text = text.replace(/^## (.*$)/gim, '<h2 class="message-h2">$1</h2>');
  text = text.replace(/^# (.*$)/gim, '<h1 class="message-h1">$1</h1>');

  // Fenced code blocks ```lang\ncode```
  text = text.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (match, lang, code) => {
    return `<div class="message-code-block"><pre><code>${code.trim()}</code></pre></div>`;
  });

  // Inline code `code`
  text = text.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');

  // Bold **text**
  text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

  // Italic *text* or _text_
  text = text.replace(/\*([^*]+)\*/g, '<em>$1</em>');

  // Blockquotes > quote
  text = text.replace(/^> (.*$)/gim, '<blockquote>$1</blockquote>');

  // Bullet points
  text = text.replace(/^\s*[-*]\s+(.*$)/gim, '<li>$1</li>');
  text = text.replace(/(<li>.*<\/li>)/gims, '<ul class="message-list">$1</ul>');

  // Double newlines to paragraphs
  const paragraphs = text.split(/\n\s*\n/);
  return paragraphs.map(p => {
    p = p.trim();
    if (!p) return '';
    if (p.startsWith('<h') || p.startsWith('<div') || p.startsWith('<ul') || p.startsWith('<blockquote')) {
      return p;
    }
    return `<p>${p.replace(/\n/g, '<br>')}</p>`;
  }).join('');
}

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function formatTime(isoStr) {
  try {
    const d = new Date(isoStr);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

function scrollToBottom() {
  const container = document.getElementById('chat-messages');
  if (container) {
    container.scrollTop = container.scrollHeight;
  }
}

function showTypingIndicator() {
  const ind = document.getElementById('ai-typing-indicator');
  if (ind) {
    ind.classList.remove('hidden');
    scrollToBottom();
  }
}

function hideTypingIndicator() {
  const ind = document.getElementById('ai-typing-indicator');
  if (ind) {
    ind.classList.add('hidden');
  }
}

// Update phase pill & labels
function updatePhase(phase) {
  currentPhase = phase;
  const label = document.getElementById('phase-label');
  const ind = document.getElementById('phase-indicator');
  if (!label || !ind) return;

  const phaseNames = {
    'intro': 'Introduction',
    'warm_up': 'Warm-Up',
    'core': 'Core Problem',
    'probing': 'Deep Probing',
    'closing': 'Closing',
    'done': 'Completed'
  };

  label.textContent = phaseNames[phase] || phase;

  // Optional: render phase divider banner in chat
  const container = document.getElementById('chat-messages');
  if (container && phase !== 'intro') {
    const divider = document.createElement('div');
    divider.className = 'phase-divider';
    divider.innerHTML = `
      <div class="phase-divider-line"></div>
      <div class="phase-divider-label">Stage: ${phaseNames[phase] || phase}</div>
      <div class="phase-divider-line"></div>
    `;
    container.appendChild(divider);
    scrollToBottom();
  }
}

// Update connection status pill
function updateConnectionStatus(status) {
  const pill = document.getElementById('connection-status');
  const text = document.getElementById('connection-text');
  if (!pill || !text) return;

  if (status === 'connected') {
    pill.className = 'connection-pill';
    text.textContent = 'Live Connected';
  } else if (status === 'connecting') {
    pill.className = 'connection-pill';
    text.textContent = 'Connecting...';
  } else if (status === 'fallback') {
    pill.className = 'connection-pill';
    text.textContent = 'HTTP Online';
  } else {
    pill.className = 'connection-pill disconnected';
    text.textContent = 'Offline';
  }
}

// Session Timer
function updateTimerDisplay() {
  const mins = String(Math.floor(sessionSeconds / 60)).padStart(2, '0');
  const secs = String(sessionSeconds % 60).padStart(2, '0');
  const display = document.getElementById('timer-display');
  if (display) {
    display.textContent = `${mins}:${secs}`;
  }
}

function syncTimerToBackend() {
  if (!currentSessionId || sessionSeconds <= 0) return;
  if (isWebSocketActive && ws && ws.readyState === WebSocket.OPEN) {
    try {
      ws.send(JSON.stringify({ type: 'timer_sync', elapsed_seconds: sessionSeconds }));
      return;
    } catch (e) {}
  }
  const token = window.api.getAccessToken();
  if (token) {
    window.api.post(`/sessions/${currentSessionId}/timer`, { elapsed_seconds: sessionSeconds }).catch(() => {});
  }
}

function startTimer() {
  clearInterval(timerInterval);
  updateTimerDisplay();

  if (currentSessionStatus === 'completed') {
    return;
  }

  timerInterval = setInterval(() => {
    if (sessionStartMs > 0) {
      sessionSeconds = Math.max(0, Math.floor((Date.now() - sessionStartMs) / 1000));
    } else {
      sessionSeconds++;
    }
    updateTimerDisplay();

    try {
      localStorage.setItem(`gaius_timer_${currentSessionId}`, sessionSeconds);
    } catch (e) {}

    if (sessionSeconds % 5 === 0) {
      syncTimerToBackend();
    }
  }, 1000);
}

// Scratchpad Panel Toggle
function toggleScratchpad(forceState = null) {
  const workspace = document.getElementById('interview-workspace');
  const workbench = document.getElementById('workbench-column');
  const navBtn = document.getElementById('btn-toggle-scratchpad');
  const feedBtn = document.getElementById('btn-feed-scratchpad');

  if (forceState !== null) {
    isScratchpadOpen = forceState;
  } else {
    isScratchpadOpen = !isScratchpadOpen;
  }

  if (isScratchpadOpen) {
    if (workspace) workspace.classList.remove('scratchpad-collapsed');
    if (workbench) workbench.classList.remove('hidden');
    if (navBtn) {
      navBtn.classList.add('active');
      navBtn.innerHTML = '<span>✕ Close Scratchpad</span>';
      navBtn.setAttribute('title', 'Close Code & Design Scratchpad');
    }
    if (feedBtn) {
      feedBtn.classList.add('active');
      feedBtn.innerHTML = '<span>✕ Scratchpad</span>';
      feedBtn.setAttribute('title', 'Close Code & Design Scratchpad');
    }
    updateCharCount();
  } else {
    if (workspace) workspace.classList.add('scratchpad-collapsed');
    if (workbench) workbench.classList.add('hidden');
    if (navBtn) {
      navBtn.classList.remove('active');
      navBtn.innerHTML = '<span>💻 Open Scratchpad</span>';
      navBtn.setAttribute('title', 'Open Code & Design Scratchpad');
    }
    if (feedBtn) {
      feedBtn.classList.remove('active');
      feedBtn.innerHTML = '<span>💻 Scratchpad</span>';
      feedBtn.setAttribute('title', 'Open Code & Design Scratchpad');
    }
  }
}
window.toggleScratchpad = toggleScratchpad;

// Workbench Tabs
function switchTab(tab) {
  const codeTab = document.getElementById('tab-code');
  const rubricTab = document.getElementById('tab-rubric');
  const codeBtn = document.getElementById('tab-code-btn');
  const rubricBtn = document.getElementById('tab-rubric-btn');

  if (tab === 'code') {
    codeTab.classList.add('active');
    rubricTab.classList.remove('active');
    codeBtn.classList.add('active');
    rubricBtn.classList.remove('active');
  } else {
    rubricTab.classList.add('active');
    codeTab.classList.remove('active');
    rubricBtn.classList.add('active');
    codeBtn.classList.remove('active');
  }
}

function updateCharCount() {
  const text = document.getElementById('code-scratchpad').value;
  const lines = text ? text.split('\n').length : 0;
  const countEl = document.getElementById('editor-char-count');
  if (countEl) {
    countEl.textContent = `${lines} ${lines === 1 ? 'line' : 'lines'} • UTF-8`;
  }
}

function clearScratchpad() {
  const pad = document.getElementById('code-scratchpad');
  if (pad) {
    pad.value = '';
    updateCharCount();
  }
}

function copyScratchpad() {
  const pad = document.getElementById('code-scratchpad');
  if (pad && pad.value) {
    navigator.clipboard.writeText(pad.value).then(() => {
      window.api.showToast('Scratchpad copied to clipboard!', 'success');
    }).catch(() => {
      window.api.showToast('Unable to copy code.', 'error');
    });
  }
}

function updateLanguageDisplay(lang) {
  const langKey = (lang || 'python').toLowerCase();
  const langLabels = {
    python: '🐍 Python',
    javascript: '🟨 JavaScript',
    java: '☕ Java',
    cpp: '⚡ C++',
    go: '🔷 Go'
  };

  const displayEl = document.getElementById('editor-lang-display');
  if (displayEl) {
    displayEl.textContent = langLabels[langKey] || (langKey.charAt(0).toUpperCase() + langKey.slice(1));
  }
  const selectEl = document.getElementById('editor-lang');
  if (selectEl) {
    selectEl.value = langKey;
  }
}

async function resetBoilerplate() {
  const pad = document.getElementById('code-scratchpad');
  if (!pad) return;

  if (currentSessionBoilerplate) {
    pad.value = currentSessionBoilerplate;
    updateCharCount();
    window.api.showToast('Starter boilerplate code restored!', 'success');
    return;
  }

  try {
    const res = await window.api.get(`/sessions/${currentSessionId}/boilerplate`);
    if (res.ok) {
      const data = await res.json();
      if (data.boilerplate_code) {
        currentSessionBoilerplate = data.boilerplate_code;
        pad.value = data.boilerplate_code;
        updateCharCount();
        window.api.showToast('Starter boilerplate code restored!', 'success');
        return;
      }
    }
    window.api.showToast('Could not load starter code.', 'error');
  } catch (err) {
    console.error('Error fetching boilerplate:', err);
    window.api.showToast('Error fetching starter code.', 'error');
  }
}

function insertCodeIntoChat() {
  const pad = document.getElementById('code-scratchpad');
  const input = document.getElementById('candidate-input');
  const lang = currentSessionLanguage || (document.getElementById('editor-lang') ? document.getElementById('editor-lang').value : 'python');
  if (!pad || !pad.value.trim()) {
    window.api.showToast('Scratchpad is empty.', 'error');
    return;
  }

  const snippet = `\`\`\`${lang}\n${pad.value.trim()}\n\`\`\`\n`;
  input.value = input.value ? `${input.value}\n\n${snippet}` : snippet;
  input.focus();
  window.api.showToast('Code snippet inserted into chat input!', 'success');
}

function updateEditorLang() {
  const lang = document.getElementById('editor-lang').value;
  updateLanguageDisplay(lang);
}

// End & Complete Modals
function openEndModal() {
  document.getElementById('modal-end-session').classList.remove('hidden');
}

function closeEndModal() {
  document.getElementById('modal-end-session').classList.add('hidden');
}

async function finishInterview() {
  closeEndModal();
  currentSessionStatus = 'completed';

  try {
    if (isWebSocketActive && ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'finish' }));
    } else {
      await window.api.post(`/sessions/${currentSessionId}/finish`);
    }
    showCompleteModal(currentSessionId);
  } catch (err) {
    console.error('Error ending interview:', err);
    showCompleteModal(currentSessionId);
  }
}

function showCompleteModal(sessionId) {
  clearInterval(timerInterval);
  currentSessionStatus = 'completed';
  if (sessionStartMs > 0) {
    sessionSeconds = Math.max(0, Math.floor((Date.now() - sessionStartMs) / 1000));
    updateTimerDisplay();
  }
  syncTimerToBackend();
  const modal = document.getElementById('modal-complete-session');
  const link = document.getElementById('link-view-report');

  if (link) {
    link.href = `/report?interview_id=${sessionId}&auto_generate=true`;
  }

  if (currentSessionMode === 'real') {
    const title = modal?.querySelector('h2');
    const text = modal?.querySelector('.complete-text');
    if (title) title.textContent = 'Real Interview Concluded';
    if (text) text.textContent = 'This Real Interview has concluded and your responses are saved. You can generate an evaluation report now or return to the dashboard.';
  }

  if (modal) {
    modal.classList.remove('hidden');
  }
}

// Warn candidate when attempting to leave/close an active Real Interview
window.addEventListener('beforeunload', (e) => {
  if (currentSessionMode === 'real' && currentSessionStatus !== 'completed' && currentPhase !== 'done') {
    e.preventDefault();
    e.returnValue = 'Real interviews cannot be left in between. Closing or navigating away will terminate this session permanently.';
    return e.returnValue;
  }
});

// Save timer and terminate real interview on tab close, window close, or navigation
window.addEventListener('pagehide', () => {
  if (currentSessionId && sessionSeconds > 0) {
    try {
      localStorage.setItem(`gaius_timer_${currentSessionId}`, sessionSeconds);
    } catch (e) {}

    const token = window.api.getAccessToken();
    const timerUrl = `/sessions/${currentSessionId}/timer?seconds=${sessionSeconds}&token=${encodeURIComponent(token || '')}`;
    if (navigator.sendBeacon) {
      navigator.sendBeacon(timerUrl);
    } else {
      fetch(timerUrl, {
        method: 'POST',
        keepalive: true,
        headers: { 'Authorization': `Bearer ${token}` }
      }).catch(() => {});
    }
  }

  if (currentSessionMode === 'real' && currentSessionStatus !== 'completed' && currentPhase !== 'done' && currentSessionId) {
    currentSessionStatus = 'completed';
    const token = window.api.getAccessToken();
    const url = `/sessions/${currentSessionId}/finish?token=${encodeURIComponent(token || '')}`;
    if (navigator.sendBeacon) {
      navigator.sendBeacon(url);
    } else {
      fetch(url, {
        method: 'POST',
        keepalive: true,
        headers: { 'Authorization': `Bearer ${token}` }
      });
    }
  }
});
