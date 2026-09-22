/**
 * Evaluation Report Rendering Logic
 */

document.addEventListener('DOMContentLoaded', async () => {
  if (!window.api || !window.api.isAuthenticated()) {
    window.location.href = '/';
    return;
  }

  const urlParams = new URLSearchParams(window.location.search);
  const interviewId = urlParams.get('interview_id');
  const autoGenerate = urlParams.get('auto_generate') === 'true';

  if (!interviewId) {
    showNoReportState('No interview session ID provided in URL.');
    return;
  }

  await loadReport(interviewId, autoGenerate);
});

async function loadReport(interviewId, autoGenerate = false) {
  const container = document.getElementById('report-container');
  container.innerHTML = `
    <div class="glass-card loading-skeleton">
      <div class="stat-icon" style="font-size: 3rem; margin-bottom: 1rem; animation: pulse 1.5s infinite;">⚡</div>
      <h2>${autoGenerate ? 'Generating Evaluation Report...' : 'Retrieving Evaluation Report...'}</h2>
      <p style="color: var(--text-secondary); margin-top: 0.5rem;">Analyzing multi-dimensional metrics, code submissions, and Big-O complexities.</p>
    </div>
  `;

  let report = null;
  try {
    const res = await window.api.get(`/reports/${interviewId}`);
    if (res.ok) {
      report = await res.json();
    } else if (res.status === 404) {
      if (autoGenerate) {
        await generateReport(interviewId);
        return;
      } else {
        // Offer on-demand generation
        promptGenerateReport(interviewId);
        return;
      }
    } else {
      showNoReportState(`Could not retrieve evaluation report (Status ${res.status}).`);
      return;
    }
  } catch (err) {
    console.error('Error fetching report:', err);
    showNoReportState('Network or server error while loading report.');
    return;
  }

  if (report) {
    try {
      renderFullReport(report);
    } catch (renderErr) {
      console.error('Error rendering evaluation report:', renderErr);
      showNoReportState('Unable to render evaluation details. Please refresh the page.');
    }
  }
}

function promptGenerateReport(interviewId) {
  const container = document.getElementById('report-container');
  container.innerHTML = `
    <div class="glass-card" style="padding: 3rem; text-align: center;">
      <div style="font-size: 3rem; margin-bottom: 1rem;">📊</div>
      <h2>Generate Interview Evaluation</h2>
      <p style="color: var(--text-secondary); max-width: 550px; margin: 0.5rem auto 1.5rem auto;">
        An evaluation report has not been generated for this session yet. Click below to run the AI Evaluator across the 7 DSA metrics and index into your profile.
      </p>
      <button class="btn btn-primary" id="btn-run-generate" onclick="generateReport('${interviewId}')">
        <span>Generate Scorecard Now</span>
        <span class="arrow">→</span>
      </button>
    </div>
  `;
}

async function generateReport(interviewId) {
  const btn = document.getElementById('btn-run-generate');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span>Evaluating with AI...</span>';
  }

  let report = null;
  try {
    const res = await window.api.post(`/reports/generate/${interviewId}`, {});
    if (res.ok) {
      report = await res.json();
      window.api.showToast('Evaluation report generated successfully!', 'success');
    } else {
      window.api.showToast('Failed to generate evaluation report.', 'error');
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<span>Generate Scorecard Now</span><span class="arrow">→</span>';
      }
      return;
    }
  } catch (err) {
    console.error('Error generating report:', err);
    window.api.showToast('Error connecting to evaluation engine.', 'error');
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<span>Generate Scorecard Now</span><span class="arrow">→</span>';
    }
    return;
  }

  if (report) {
    try {
      renderFullReport(report);
    } catch (renderErr) {
      console.error('Error rendering generated report:', renderErr);
      showNoReportState('Evaluation generated, but failed to render display.');
    }
  }
}

function renderFullReport(report) {
  const container = document.getElementById('report-container');
  const score = (report.overall_score !== undefined && report.overall_score !== null)
    ? Number(report.overall_score)
    : 0.0;
  const scorePct = Math.min(100, Math.max(0, Math.round((score / 4.0) * 100)));

  // Determine performance tier
  let tierClass = 'tier-strong';
  let tierLabel = 'Strong • Meets FAANG Bar';
  let barColorClass = 'fill-strong';

  if (score >= 3.6) {
    tierClass = 'tier-exceptional';
    tierLabel = 'Exceptional • Staff Tier';
    barColorClass = 'fill-exceptional';
  } else if (score >= 3.0) {
    tierClass = 'tier-strong';
    tierLabel = 'Strong • Meets FAANG Bar';
    barColorClass = 'fill-strong';
  } else if (score >= 2.0) {
    tierClass = 'tier-developing';
    tierLabel = 'Developing • Approaching Bar';
    barColorClass = 'fill-developing';
  } else if (score > 1.2) {
    tierClass = 'tier-unsatisfactory';
    tierLabel = 'Needs Targeted Practice';
    barColorClass = 'fill-unsatisfactory';
  } else {
    tierClass = 'tier-unassessed';
    tierLabel = 'Unassessed • No Evidence';
    barColorClass = 'fill-unassessed';
  }

  const topicName = report.topic || 'Technical DSA';
  let dateStr = 'Recent';
  try {
    if (report.created_at) {
      dateStr = new Date(report.created_at).toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
      });
    }
  } catch (e) {
    dateStr = 'Recent';
  }

  // Metrics array
  const metrics = report.dsa_metrics || {};
  const metricKeys = [
    { key: 'algorithmic_logic', icon: '⚡', fallbackName: 'Algorithmic Correctness & Logic' },
    { key: 'time_space_complexity', icon: '⏱️', fallbackName: 'Time & Space Complexity (Big-O)' },
    { key: 'data_structures', icon: '🧱', fallbackName: 'Data Structure Selection' },
    { key: 'edge_cases', icon: '🛡️', fallbackName: 'Edge Case Handling & Rigor' },
    { key: 'code_quality', icon: '💻', fallbackName: 'Code Quality & Implementation' },
    { key: 'problem_solving', icon: '🧩', fallbackName: 'Problem-Solving & Optimization' },
    { key: 'communication', icon: '🗣️', fallbackName: 'Communication & Collaboration' },
  ];

  const metricsHtml = metricKeys.map(m => {
    const item = metrics[m.key] || {
      score: report.dimension_scores ? (report.dimension_scores[m.key] || 3.0) : 3.0,
      name: m.fallbackName,
      rationale: 'Evaluated according to standard criteria.',
      evidence_quote: 'Demonstrated during interview responses.',
      growth_tip: 'Focus on targeted practice drills.'
    };

    const mScore = (item.score !== undefined && item.score !== null) ? Number(item.score) : 1.0;
    const hasEvidence = item.has_evidence !== undefined ? Boolean(item.has_evidence) : (mScore > 1.0);
    const mPct = hasEvidence ? Math.min(100, Math.max(0, Math.round((mScore / 4.0) * 100))) : 0;
    
    let mBarClass = 'fill-strong';
    if (!hasEvidence) mBarClass = 'fill-unassessed';
    else if (mScore >= 3.6) mBarClass = 'fill-exceptional';
    else if (mScore >= 3.0) mBarClass = 'fill-strong';
    else if (mScore >= 2.0) mBarClass = 'fill-developing';
    else mBarClass = 'fill-unsatisfactory';

    const scoreBadge = hasEvidence
      ? `<span class="metric-score-badge">${mScore.toFixed(1)} / 4.0</span>`
      : `<span class="metric-score-badge badge-no-evidence">No Evidence • 1.0 / 4.0</span>`;

    const evidenceHtml = hasEvidence
      ? `<div class="metric-evidence-box"><strong>Evidence:</strong> "${item.evidence_quote || 'Observed in technical responses.'}"</div>`
      : `<div class="metric-evidence-box no-evidence">⚠️ <em>No evidence observed in transcript</em></div>`;

    return `
      <div class="metric-card">
        <div>
          <div class="metric-header">
            <div class="metric-name-wrap">
              <span>${m.icon}</span>
              <span>${item.name || m.fallbackName}</span>
            </div>
            ${scoreBadge}
          </div>

          <div class="score-bar-bg">
            <div class="score-bar-fill ${mBarClass}" style="width: ${mPct}%;"></div>
          </div>

          <p class="metric-rationale">${item.rationale || ''}</p>
          ${evidenceHtml}
        </div>

        ${
          item.growth_tip
            ? `<div class="metric-growth-tip">💡 <strong>Action Tip:</strong> ${item.growth_tip}</div>`
            : ''
        }
      </div>
    `;
  }).join('');

  // Strengths list
  const strengthsList = (report.strengths || []).map(s => `
    <li class="analysis-item">
      <span class="icon-check">✓</span>
      <span>${s}</span>
    </li>
  `).join('');

  // Improvements list
  const improvementsList = (report.improvement_areas || []).map(imp => `
    <li class="analysis-item">
      <span class="icon-target">🎯</span>
      <span>${imp}</span>
    </li>
  `).join('');

  // Focus roadmap tags
  const focusTags = (report.recommended_focus_areas || []).map(f => `
    <span class="roadmap-tag">
      <span>📚</span>
      <span>${f}</span>
    </span>
  `).join('');

  container.innerHTML = `
    <!-- Top Hero Score Grid -->
    <div class="report-hero-grid">
      <!-- Left: Big Scorecard -->
      <div class="glass-card score-summary-card">
        <div class="score-gauge-wrap">
          <div class="score-circle" style="--score-pct: ${scorePct};">
            <div class="score-circle-inner">
              <span class="score-number">${score.toFixed(1)}</span>
              <span class="score-max">/ 4.0</span>
            </div>
          </div>
        </div>

        <span class="tier-badge ${tierClass}">${tierLabel}</span>

        <div class="rag-indexed-pill">
          <span>🧠</span>
          <span>Chunked & Indexed in ChromaDB</span>
        </div>
      </div>

      <!-- Right: Meta & AI Executive Summary -->
      <div class="glass-card summary-meta-card">
        <div>
          <div class="meta-header-row">
            <div>
              <span class="report-topic-badge">${topicName}</span>
              <span style="color: var(--text-muted); font-size: 0.85rem; margin-left: 0.75rem;">Session Date: ${dateStr}</span>
            </div>
            <div class="quick-actions-bar">
              <a href="/dashboard" class="btn btn-secondary btn-sm">Dashboard</a>
              <a href="/coach" class="btn btn-primary btn-sm">🧠 Coach Chat</a>
            </div>
          </div>

          <h3 style="font-size: 1.15rem; font-weight: 700; margin-bottom: 0.75rem;">AI Evaluator Review</h3>
          <p class="executive-summary-text">${report.detailed_feedback || 'Solid technical performance.'}</p>
        </div>

        <div style="font-size: 0.85rem; color: var(--text-muted);">
          Indexed into candidate vector memory across 7 discrete metric documents for personalized RAG coaching.
        </div>
      </div>
    </div>

    <!-- 7 Core DSA Dimensions Breakdown -->
    <div class="section-title">
      <span>📊</span>
      <span>Comprehensive 7-Dimension Rubric Scorecard</span>
    </div>
    <div class="metrics-grid">
      ${metricsHtml}
    </div>

    <!-- Strengths & Growth Areas Side-by-Side -->
    <div class="analysis-grid">
      <div class="glass-card analysis-col">
        <h3 style="color: #34d399; font-size: 1.15rem; font-weight: 700; margin-bottom: 1.25rem; display: flex; align-items: center; gap: 0.5rem;">
          <span>🌟</span> Key Demonstrated Strengths
        </h3>
        <ul class="analysis-list">
          ${strengthsList || '<li class="analysis-item">Solid algorithmic logic demonstrated.</li>'}
        </ul>
      </div>

      <div class="glass-card analysis-col">
        <h3 style="color: #f59e0b; font-size: 1.15rem; font-weight: 700; margin-bottom: 1.25rem; display: flex; align-items: center; gap: 0.5rem;">
          <span>🎯</span> Targeted Improvement Areas
        </h3>
        <ul class="analysis-list">
          ${improvementsList || '<li class="analysis-item">Review edge cases and space complexity trade-offs.</li>'}
        </ul>
      </div>
    </div>

    <!-- Recommended Study Roadmap -->
    <div class="glass-card roadmap-container">
      <h3 style="font-size: 1.15rem; font-weight: 700; color: #f8fafc; display: flex; align-items: center; gap: 0.5rem;">
        <span>🗺️</span> Recommended Technical Growth Areas
      </h3>
      <p style="color: var(--text-secondary); font-size: 0.92rem; margin-top: 0.35rem;">
        Topics highlighted by the evaluator for your next preparation cycle. Ask your AI Coach about these concepts.
      </p>
      <div class="roadmap-tags">
        ${focusTags || '<span class="roadmap-tag"><span>📚</span><span>DSA Optimization Patterns</span></span>'}
      </div>
      <div style="margin-top: 1.5rem;">
        <a href="/coach" class="btn btn-primary">
          <span>Practice These Concepts with AI Coach</span>
          <span class="arrow">→</span>
        </a>
      </div>
    </div>
  `;
}

function showNoReportState(message) {
  const container = document.getElementById('report-container');
  container.innerHTML = `
    <div class="glass-card" style="padding: 3rem; text-align: center;">
      <div style="font-size: 3rem; margin-bottom: 1rem;">⚠️</div>
      <h2>Report Not Available</h2>
      <p style="color: var(--text-secondary); max-width: 500px; margin: 0.5rem auto 1.5rem auto;">${message}</p>
      <a href="/dashboard" class="btn btn-primary">Return to Dashboard</a>
    </div>
  `;
}
