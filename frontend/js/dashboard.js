/**
 * Candidate Dashboard Logic — The Amber Editorial
 */

document.addEventListener('DOMContentLoaded', async () => {
  if (!window.api || !window.api.isAuthenticated()) {
    window.location.href = '/';
    return;
  }

  loadUserProfile();
  initPresetPillInteractions();
  await loadDashboardData();
});

function loadUserProfile() {
  const user = window.api.getUser();
  if (user) {
    const fullName = user.full_name || 'Candidate';
    const welcomeEl = document.getElementById('welcome-name');
    const nameEl = document.getElementById('user-full-name');
    const initialsEl = document.getElementById('user-avatar-initials');

    if (welcomeEl) welcomeEl.textContent = fullName;
    if (nameEl) nameEl.textContent = fullName;
    if (initialsEl) {
      const parts = fullName.trim().split(/\s+/).filter(Boolean);
      const initials = parts.length > 1
        ? (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
        : (parts[0] ? parts[0].slice(0, 2).toUpperCase() : 'GM');
      initialsEl.textContent = initials;
    }
  }
}

function initPresetPillInteractions() {
  const domainSelect = document.getElementById('domain-select');
  const presetButtons = document.querySelectorAll('.preset-pill');

  presetButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetPreset = btn.getAttribute('data-preset');
      if (targetPreset && domainSelect) {
        domainSelect.value = targetPreset;

        // Visual pulse feedback highlight
        domainSelect.classList.add('domain-pulse-highlight');
        setTimeout(() => {
          domainSelect.classList.remove('domain-pulse-highlight');
        }, 600);
      }
    });
  });
}

async function loadDashboardData() {
  try {
    const [sessionsRes, reportsRes] = await Promise.all([
      window.api.get('/sessions/'),
      window.api.get('/reports/')
    ]);

    if (sessionsRes.ok) {
      const sessions = await sessionsRes.json();
      const reports = reportsRes.ok ? await reportsRes.json() : [];
      renderSessions(sessions, reports);
      updateStats(sessions, reports);
    }
  } catch (err) {
    console.error('Error loading dashboard data:', err);
    window.api.showToast('Could not load interview history.', 'error');
  }
}

function calculateDimensionExtremes(reports) {
  if (!reports || reports.length === 0) {
    return {
      star: { name: 'Pending', score: '' },
      poorest: { name: 'Pending', score: '' }
    };
  }

  const dimensionTotals = {};
  const dimensionCounts = {};

  const dimensionLabels = {
    algorithmic_logic: 'Algorithmic Logic',
    time_space_complexity: 'Big-O Complexity',
    data_structures: 'Data Structures',
    edge_cases: 'Edge Cases',
    code_quality: 'Code Quality',
    problem_solving: 'Problem Solving',
    communication: 'Communication',
    technical: 'Technical Depth',
    behavioral_star: 'Behavioral Reasoning',
    adaptability: 'Adaptability',
    confidence: 'Confidence',
    role_alignment: 'Role Alignment'
  };

  reports.forEach(r => {
    if (r.dsa_metrics && typeof r.dsa_metrics === 'object') {
      Object.entries(r.dsa_metrics).forEach(([key, val]) => {
        if (val && val.score !== undefined && val.has_evidence !== false) {
          const score = Number(val.score);
          if (!isNaN(score)) {
            dimensionTotals[key] = (dimensionTotals[key] || 0) + score;
            dimensionCounts[key] = (dimensionCounts[key] || 0) + 1;
          }
        }
      });
    } else if (r.dimension_scores && typeof r.dimension_scores === 'object') {
      Object.entries(r.dimension_scores).forEach(([key, score]) => {
        const num = Number(score);
        if (!isNaN(num)) {
          dimensionTotals[key] = (dimensionTotals[key] || 0) + num;
          dimensionCounts[key] = (dimensionCounts[key] || 0) + 1;
        }
      });
    }
  });

  const averages = [];
  Object.keys(dimensionTotals).forEach(key => {
    if (dimensionCounts[key] > 0) {
      averages.push({
        key,
        name: dimensionLabels[key] || key.replace(/_/g, ' '),
        avgScore: dimensionTotals[key] / dimensionCounts[key]
      });
    }
  });

  if (averages.length === 0) {
    return {
      star: { name: 'Pending', score: '' },
      poorest: { name: 'Pending', score: '' }
    };
  }

  averages.sort((a, b) => b.avgScore - a.avgScore);
  const star = averages[0];
  const poorest = averages[averages.length - 1];

  return {
    star: { name: star.name, score: `• ${star.avgScore.toFixed(1)} / 4.0` },
    poorest: { name: poorest.name, score: `• ${poorest.avgScore.toFixed(1)} / 4.0` }
  };
}

function updateStats(sessions, reports) {
  const countEl = document.getElementById('stat-interviews-count');
  const labelEl = document.getElementById('stat-interviews-label');
  const avgEl = document.getElementById('stat-avg-score');
  
  const starNameEl = document.getElementById('stat-star-metric-name');
  const starScoreEl = document.getElementById('stat-star-metric-score');
  const poorestNameEl = document.getElementById('stat-poorest-metric-name');
  const poorestScoreEl = document.getElementById('stat-poorest-metric-score');

  const completed = sessions ? sessions.filter(s => s.status === 'completed').length : 0;
  if (countEl) countEl.textContent = completed;
  if (labelEl) labelEl.textContent = `${completed} COMPLETED`;

  if (reports && reports.length > 0) {
    const sum = reports.reduce((acc, r) => acc + (r.overall_score || 0), 0);
    const avg = (sum / reports.length).toFixed(1);
    if (avgEl) avgEl.textContent = avg;
  } else {
    if (avgEl) avgEl.textContent = '—';
  }

  // Calculate Star (highest) and Poorest (lowest) metrics
  const extremes = calculateDimensionExtremes(reports);
  if (starNameEl) starNameEl.textContent = extremes.star.name;
  if (starScoreEl) starScoreEl.textContent = extremes.star.score;
  if (poorestNameEl) poorestNameEl.textContent = extremes.poorest.name;
  if (poorestScoreEl) poorestScoreEl.textContent = extremes.poorest.score;
}

function renderSessions(sessions, reports) {
  const container = document.getElementById('sessions-container');
  if (!container) return;

  if (!sessions || sessions.length === 0) {
    container.innerHTML = `
      <div class="p-8 text-center" style="color: rgb(100, 116, 139);">
        <div style="font-size: 2.2rem; margin-bottom: 0.5rem;">✨</div>
        <p class="font-semibold" style="color: rgb(71, 85, 105);">No interview sessions yet</p>
        <p class="text-xs mt-1">Select a technical domain above and click Launch Interview to begin your first session.</p>
      </div>
    `;
    return;
  }

  const reportsMap = {};
  if (reports) {
    reports.forEach(r => {
      reportsMap[r.interview_id] = r;
    });
  }

  // Display only the single most recent session on the dashboard snapshot
  const recentSessions = sessions.slice(0, 1);

  container.innerHTML = recentSessions.map(s => {
    const date = new Date(s.started_at).toLocaleDateString(undefined, {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });

    const isRealMode = s.interview_mode === 'real';
    // Real interviews cannot be left in between; if viewed from dashboard, they are ended
    const isCompleted = s.status === 'completed' || isRealMode;
    const report = reportsMap[s.id];
    const scoreBadge = (isCompleted && report && report.overall_score !== undefined)
      ? `<span class="session-badge-score">⭐ ${Number(report.overall_score).toFixed(1)} / 4.0</span>`
      : '';

    const categoryTag = s.topic.includes('System Design')
      ? 'Architecture'
      : (s.topic.includes('OS') || s.topic.includes('Concurrency') ? 'Systems' : 'Algorithms');

    // Strict action button logic:
    // Real interviews cannot be resumed.
    // If completed or real: show View Report (if report exists) or Generate Report (if report does not exist)
    // If coached and NOT completed: show Resume Interview
    let actionBtnHtml = '';
    if (isCompleted) {
      if (report) {
        actionBtnHtml = `
          <a href="/report?interview_id=${s.id}" class="session-action-btn-report">
            <span>View Evaluation</span>
            <span>→</span>
          </a>
        `;
      } else {
        actionBtnHtml = `
          <a href="/report?interview_id=${s.id}" class="session-action-btn-report" style="background-color: rgb(237, 233, 254); color: rgb(91, 33, 182); border: 1px solid rgb(221, 214, 254);">
            <span>Generate Report</span>
            <span>⚡</span>
          </a>
        `;
      }
    } else {
      actionBtnHtml = `
        <a href="/interview?session_id=${s.id}" class="session-action-btn-resume">
          <span>Resume Interview</span>
          <span>→</span>
        </a>
      `;
    }

    return `
      <div class="session-card-item">
        <div class="session-card-top">
          <div class="flex items-center gap-2.5 flex-wrap">
            <span class="session-topic-title">${s.topic}</span>
            <span class="session-badge-category">${categoryTag}</span>
            ${scoreBadge}
          </div>
          <span class="${isCompleted ? 'session-badge-status-completed' : 'session-badge-status-progress'}">
            ${isCompleted ? 'COMPLETED' : 'IN PROGRESS'}
          </span>
        </div>

        <div class="session-card-bottom">
          <div class="session-meta-text">
            <span>${date}</span>
            <span style="color: #CBD5E1;">•</span>
            <span>Phase: <strong style="color: #0F172A;">${s.current_phase || 'in-progress'}</strong></span>
          </div>
          <div>
            ${actionBtnHtml}
          </div>
        </div>
      </div>
    `;
  }).join('');
}

let selectedInterviewMode = 'real';

function selectInterviewMode(mode) {
  selectedInterviewMode = mode;
  const coachedBtn = document.getElementById('mode-btn-coached');
  const realBtn = document.getElementById('mode-btn-real');

  if (!coachedBtn || !realBtn) return;

  if (mode === 'coached') {
    coachedBtn.classList.add('active');
    coachedBtn.style.backgroundColor = 'rgb(255, 251, 235)';
    coachedBtn.style.borderColor = 'rgb(245, 158, 11)';
    coachedBtn.style.boxShadow = 'rgba(245, 158, 11, 0.18) 0px 4px 12px';

    realBtn.classList.remove('active');
    realBtn.style.backgroundColor = 'rgb(255, 255, 255)';
    realBtn.style.borderColor = 'rgb(226, 232, 240)';
    realBtn.style.boxShadow = 'none';
  } else {
    realBtn.classList.add('active');
    realBtn.style.backgroundColor = 'rgb(255, 247, 237)';
    realBtn.style.borderColor = 'rgb(249, 115, 22)';
    realBtn.style.boxShadow = 'rgba(249, 115, 22, 0.15) 0px 4px 12px';

    coachedBtn.classList.remove('active');
    coachedBtn.style.backgroundColor = 'rgb(255, 255, 255)';
    coachedBtn.style.borderColor = 'rgb(226, 232, 240)';
    coachedBtn.style.boxShadow = 'none';
  }
}

let selectedCodingLanguage = 'python';

function handleLanguageRadioChange(lang) {
  selectedCodingLanguage = lang;
  window.selectedCodingLanguage = lang;
  const hiddenInput = document.getElementById('language-select');
  if (hiddenInput) {
    hiddenInput.value = lang;
  }

  const cards = document.querySelectorAll('.lang-radio-card');
  cards.forEach(card => {
    const r = card.querySelector('input[type="radio"]');
    if (r && r.checked) {
      card.classList.add('active');
      card.style.backgroundColor = 'rgb(255, 247, 237)';
      card.style.borderColor = 'rgb(249, 115, 22)';
      card.style.boxShadow = 'rgba(249, 115, 22, 0.15) 0px 4px 12px';
    } else {
      card.classList.remove('active');
      card.style.backgroundColor = 'rgb(255, 255, 255)';
      card.style.borderColor = 'rgb(226, 232, 240)';
      card.style.boxShadow = 'none';
    }
  });
}
window.handleLanguageRadioChange = handleLanguageRadioChange;

function selectCodingLanguage(lang) {
  const radio = document.getElementById('lang-radio-' + lang);
  if (radio) {
    radio.checked = true;
    handleLanguageRadioChange(lang);
  }
}
window.selectCodingLanguage = selectCodingLanguage;

async function startInterview(event) {
  if (event) event.preventDefault();
  const select = document.getElementById('domain-select');
  const topic = select ? select.value : 'Arrays & Hashing';
  const selectedRadio = document.querySelector('input[name="preferred_language"]:checked');
  const langSelect = document.getElementById('language-select');
  const language = (selectedRadio ? selectedRadio.value : '') || window.selectedCodingLanguage || selectedCodingLanguage || (langSelect ? langSelect.value : 'python');
  const interview_mode = selectedInterviewMode || 'real';
  const btn = document.getElementById('launch-interview-btn');
  const btnText = document.getElementById('launch-btn-text');

  if (btn) btn.disabled = true;
  if (btnText) btnText.textContent = 'Launching...';

  try {
    const res = await window.api.post('/sessions/start', {
      topic,
      interview_mode,
      language
    });
    const session = await res.json();

    if (res.ok && session.id) {
      const modeTitle = interview_mode === 'coached' ? 'Coached' : 'Real';
      window.api.showToast(`Starting ${modeTitle} Interview (${topic})!`, 'success');
      setTimeout(() => {
        window.location.href = `/interview?session_id=${session.id}`;
      }, 400);
    } else {
      window.api.showToast('Failed to start interview session.', 'error');
      if (btn) btn.disabled = false;
      if (btnText) btnText.textContent = 'Launch Interview';
    }
  } catch (err) {
    window.api.showToast('Error connecting to interview server.', 'error');
    if (btn) btn.disabled = false;
    if (btnText) btnText.textContent = 'Launch Interview';
  }
}

function logout() {
  window.api.clearAuth();
  window.location.href = '/';
}
