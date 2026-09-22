/**
 * Interview History Page Logic
 * Renders all candidate sessions with filtering, search, and strict completion action button handling.
 */

let allSessions = [];
let allReports = {};
let currentFilter = 'all';
let searchQuery = '';

document.addEventListener('DOMContentLoaded', async () => {
  if (!window.api || !window.api.isAuthenticated()) {
    window.location.href = '/';
    return;
  }

  initUserHeader();
  await loadHistoryData();
});

function initUserHeader() {
  const user = window.api.getUser();
  if (!user) return;

  const initialsEl = document.getElementById('user-avatar-initials');
  const nameEl = document.getElementById('user-full-name');

  if (initialsEl && user.full_name) {
    const initials = user.full_name
      .split(' ')
      .map(n => n[0])
      .join('')
      .substring(0, 2)
      .toUpperCase();
    initialsEl.textContent = initials || 'GM';
  }

  if (nameEl && user.full_name) {
    nameEl.textContent = user.full_name;
    nameEl.style.display = 'inline-block';
  }
}

async function loadHistoryData() {
  const container = document.getElementById('history-sessions-container');

  try {
    const [sessionsRes, reportsRes] = await Promise.all([
      window.api.get('/sessions/'),
      window.api.get('/reports/')
    ]);

    if (sessionsRes.ok) {
      allSessions = await sessionsRes.json();
      const reportsList = reportsRes.ok ? await reportsRes.json() : [];
      allReports = {};
      reportsList.forEach(r => {
        allReports[r.interview_id] = r;
      });

      updateSummaryBadges(allSessions);
      renderFilteredSessions();
    } else {
      if (container) {
        container.innerHTML = `
          <div class="empty-history-box">
            <div style="font-size: 2.5rem; margin-bottom: 0.75rem;">⚠️</div>
            <h3 style="font-size: 1.25rem; font-weight: 800;">Could Not Load Session History</h3>
            <p style="color: rgb(100, 116, 139); margin-top: 0.35rem;">Status ${sessionsRes.status} received from server.</p>
            <button class="btn btn-primary" style="margin-top: 1.25rem;" onclick="loadHistoryData()">Retry</button>
          </div>
        `;
      }
    }
  } catch (err) {
    console.error('Error fetching history:', err);
    if (container) {
      container.innerHTML = `
        <div class="empty-history-box">
          <div style="font-size: 2.5rem; margin-bottom: 0.75rem;">⚠️</div>
          <h3 style="font-size: 1.25rem; font-weight: 800;">Network or Server Connection Error</h3>
          <p style="color: rgb(100, 116, 139); margin-top: 0.35rem;">Unable to establish communication with the session database.</p>
          <button class="btn btn-primary" style="margin-top: 1.25rem;" onclick="loadHistoryData()">Retry</button>
        </div>
      `;
    }
  }
}

function updateSummaryBadges(sessions) {
  const totalEl = document.getElementById('text-total-sessions');
  const completedEl = document.getElementById('text-completed-sessions');

  const total = sessions ? sessions.length : 0;
  const completed = sessions ? sessions.filter(s => s.status === 'completed').length : 0;

  if (totalEl) totalEl.textContent = `${total} Total Session${total === 1 ? '' : 's'}`;
  if (completedEl) completedEl.textContent = `${completed} Completed`;
}

function setFilter(filter) {
  currentFilter = filter;
  document.querySelectorAll('.filter-pill-btn').forEach(btn => {
    if (btn.getAttribute('data-filter') === filter) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });
  renderFilteredSessions();
}

function handleSearch(query) {
  searchQuery = (query || '').trim().toLowerCase();
  renderFilteredSessions();
}

function renderFilteredSessions() {
  const container = document.getElementById('history-sessions-container');
  if (!container) return;

  let filtered = allSessions.slice();

  // Status Filter
  if (currentFilter === 'completed') {
    filtered = filtered.filter(s => s.status === 'completed');
  } else if (currentFilter === 'in-progress') {
    filtered = filtered.filter(s => s.status !== 'completed');
  }

  // Keyword Search
  if (searchQuery) {
    filtered = filtered.filter(s => {
      const topic = (s.topic || '').toLowerCase();
      const phase = (s.current_phase || '').toLowerCase();
      return topic.includes(searchQuery) || phase.includes(searchQuery);
    });
  }

  if (filtered.length === 0) {
    container.innerHTML = `
      <div class="empty-history-box">
        <div style="font-size: 2.5rem; margin-bottom: 0.75rem;">📂</div>
        <h3 style="font-size: 1.25rem; font-weight: 800;">No Sessions Found</h3>
        <p style="color: rgb(100, 116, 139); max-width: 440px; margin: 0.35rem auto 1.25rem auto;">
          ${searchQuery || currentFilter !== 'all'
            ? 'No interview sessions match your current filter and search query.'
            : 'You haven\'t started any interviews yet. Select a technical topic on your dashboard to launch your first session!'}
        </p>
        <a href="/dashboard" class="btn btn-primary">Go to Dashboard</a>
      </div>
    `;
    return;
  }

  container.innerHTML = filtered.map(s => {
    const isRealMode = s.interview_mode === 'real';
    // Real interviews cannot be left in between; if viewed in history, they are ended
    const isCompleted = s.status === 'completed' || isRealMode;
    const report = allReports[s.id];

    const dateStr = new Date(s.started_at).toLocaleDateString(undefined, {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });

    const categoryTag = s.topic.includes('System Design')
      ? 'Architecture'
      : (s.topic.includes('OS') || s.topic.includes('Concurrency') ? 'Systems' : 'Algorithms');

    // Score Badge
    const scoreBadge = (isCompleted && report && report.overall_score !== undefined)
      ? `<span class="badge-score-pill">⭐ ${Number(report.overall_score).toFixed(1)} / 4.0</span>`
      : '';

    // Status Pill
    const statusPill = isCompleted
      ? `<span class="badge-status-completed"><span>●</span> COMPLETED</span>`
      : `<span class="badge-status-progress"><span>●</span> IN PROGRESS</span>`;

    // Action Button Logic: Real interviews cannot be resumed
    let actionButtonHtml = '';
    if (isCompleted) {
      if (report) {
        actionButtonHtml = `
          <a href="/report?interview_id=${s.id}" class="btn-action-report">
            <span>View Evaluation</span>
            <span class="arrow">→</span>
          </a>
        `;
      } else {
        actionButtonHtml = `
          <a href="/report?interview_id=${s.id}" class="btn-action-generate">
            <span>Generate Report</span>
            <span class="arrow">⚡</span>
          </a>
        `;
      }
    } else {
      actionButtonHtml = `
        <a href="/interview?session_id=${s.id}" class="btn-action-resume">
          <span>Resume Interview</span>
          <span class="arrow">→</span>
        </a>
      `;
    }

    return `
      <div class="history-card">
        <div class="history-card-header">
          <div class="history-topic-wrap">
            <span class="history-topic-title">${s.topic}</span>
            <span class="badge-category">${categoryTag}</span>
            ${scoreBadge}
          </div>
          <div>${statusPill}</div>
        </div>

        <div class="history-card-footer">
          <div class="history-meta-row">
            <span>📅 Started: <strong>${dateStr}</strong></span>
            <span style="color: rgb(203, 213, 225);">•</span>
            <span>Current Phase: <strong>${s.current_phase || 'In Progress'}</strong></span>
          </div>

          <div style="margin-top: 0.75rem;" class="sm:mt-0">
            ${actionButtonHtml}
          </div>
        </div>
      </div>
    `;
  }).join('');
}

function logout() {
  if (window.api) {
    window.api.clearAuth();
  }
  window.location.href = '/';
}
