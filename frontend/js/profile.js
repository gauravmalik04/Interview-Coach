/**
 * GAIUS — Candidate Profile Client Logic & Multi-Step Wizard
 * Dual-mode: View Mode vs Edit Mode Wizard with local + API persistence
 */

// Available quick suggestions
const DEFAULT_SUGGESTIONS = [
  'TypeScript', 'Go', 'FastAPI', 'System Design', 'Python',
  'PostgreSQL', 'Docker', 'Algorithms', 'React', 'Kubernetes',
  'GraphQL', 'C++'
];

// Core State
let currentStep = 0;
let isEditing = false;
let currentSkills = [];

// Active Profile Object — initially unconfigured (empty defaults)
let candidateProfile = {
  is_configured: false,
  personal: {
    name: '',
    email: '',
    education: '',
    experience_level: ''
  },
  target: {
    role: '',
    company: ''
  },
  skills: [],
  preferences: {
    input_mode: 'text',
    preferred_difficulty: 'Adaptive AI'
  }
};

function getUserProfileStorageKey() {
  const user = window.api ? window.api.getUser() : null;
  return (user && user.id) ? `gaius_candidate_profile_${user.id}` : 'gaius_candidate_profile';
}

document.addEventListener('DOMContentLoaded', async () => {
  // If not authenticated, redirect to sign in / register page
  if (window.api && !window.api.isAuthenticated()) {
    window.location.href = '/';
    return;
  }

  // Fetch candidate profile from backend database
  await fetchProfileFromBackendOrStorage();

  initEventListeners();
  renderViewMode();

  // If candidate has ALREADY configured their profile, show the saved profile in View Mode!
  // Only enter wizard if candidate has NOT configured their profile yet.
  const configured = isProfileConfigured();
  if (!configured) {
    enterEditMode();
  }
});

/**
 * Check if candidate has completed setting their profile
 */
function isProfileConfigured() {
  if (!candidateProfile) return false;
  const p = candidateProfile.personal || {};
  const t = candidateProfile.target || {};
  const hasEdu = typeof p.education === 'string' && p.education.trim() !== '';
  const hasRole = typeof t.role === 'string' && t.role.trim() !== '';
  return !!(candidateProfile.is_configured || (hasEdu && hasRole));
}

/**
 * Fetch candidate profile from backend API, falling back to localStorage
 */
async function fetchProfileFromBackendOrStorage() {
  let loaded = false;
  if (window.api && window.api.isAuthenticated()) {
    try {
      const res = await window.api.get('/auth/profile');
      if (res.ok) {
        const data = await res.json();
        if (data && data.personal) {
          candidateProfile = data;
          if (data.is_configured) {
            localStorage.setItem(getUserProfileStorageKey(), JSON.stringify(candidateProfile));
          } else {
            localStorage.removeItem(getUserProfileStorageKey());
          }
          loaded = true;
        }
      }
    } catch (err) {
      console.warn('API profile fetch failed, using local fallback:', err);
    }
  }

  if (!loaded) {
    loadProfileFromStorage();
  }
}

/**
 * Load from localStorage or initialize with clean unconfigured state
 */
function loadProfileFromStorage() {
  const stored = localStorage.getItem(getUserProfileStorageKey());
  if (stored) {
    try {
      const parsed = JSON.parse(stored);
      if (parsed && parsed.is_configured === true) {
        candidateProfile = parsed;
      } else {
        candidateProfile.is_configured = false;
        if (parsed.personal && parsed.personal.name) {
          candidateProfile.personal.name = parsed.personal.name;
        }
      }
    } catch (e) {
      console.error('Error parsing stored profile:', e);
    }
  } else {
    candidateProfile.is_configured = false;
  }

  // Overlay auth user name and email if available
  if (window.api) {
    const user = window.api.getUser();
    if (user) {
      if (user.full_name && !candidateProfile.personal.name) {
        candidateProfile.personal.name = user.full_name;
      }
      if (user.email && !candidateProfile.personal.email) {
        candidateProfile.personal.email = user.email;
      }
    }
  }
}

/**
 * Setup DOM listeners and event handlers
 */
function initEventListeners() {
  // Mode Toggle Button
  const toggleBtn = document.getElementById('btn-mode-toggle');
  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      if (isEditing) {
        exitEditMode();
      } else {
        enterEditMode();
      }
    });
  }

  // Alert Banner "Set Up Profile Now 🚀" button
  const alertSetupBtn = document.getElementById('btn-alert-setup');
  if (alertSetupBtn) {
    alertSetupBtn.addEventListener('click', () => {
      enterEditMode();
    });
  }

  // Wizard Step Header Nodes
  document.querySelectorAll('.step-node').forEach(node => {
    node.addEventListener('click', () => {
      const targetStep = parseInt(node.getAttribute('data-step'), 10);
      if (targetStep < currentStep) {
        currentStep = targetStep;
        updateWizardUI();
      } else if (targetStep > currentStep) {
        if (validateCurrentStep()) {
          currentStep = targetStep;
          updateWizardUI();
        }
      }
    });
  });

  // Wizard Footer Back & Continue Buttons
  const backBtn = document.getElementById('btn-wizard-back');
  if (backBtn) {
    backBtn.addEventListener('click', handleWizardBack);
  }

  const continueBtn = document.getElementById('btn-wizard-continue');
  if (continueBtn) {
    continueBtn.addEventListener('click', handleWizardContinue);
  }

  // Skills input & inline add button
  const skillInput = document.getElementById('skill-input');
  const addSkillBtn = document.getElementById('btn-add-skill');

  if (addSkillBtn && skillInput) {
    addSkillBtn.addEventListener('click', () => {
      addSkillFromInput();
    });

    skillInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        addSkillFromInput();
      }
    });
  }

}

/**
 * Render View Mode Card with current candidateProfile data.
 * If unconfigured, displays "Not set yet" placeholders and setup banner.
 */
function renderViewMode() {
  const configured = isProfileConfigured();
  const p = candidateProfile.personal || {};
  const t = candidateProfile.target || {};
  const pref = candidateProfile.preferences || {};

  // Unconfigured Alert Banner
  const alertBox = document.getElementById('unconfigured-alert-box');
  if (alertBox) {
    alertBox.style.display = configured ? 'none' : 'flex';
  }

  // Toggle button text
  const toggleBtn = document.getElementById('btn-mode-toggle');
  if (toggleBtn) {
    toggleBtn.innerHTML = configured ? 'Edit Profile ✏️' : 'Set Up Profile ✨';
    toggleBtn.classList.remove('is-editing');
  }

  // Avatar Initials
  const avatarEl = document.getElementById('view-avatar-initials');
  const nameParts = (p.name || '').trim().split(/\s+/).filter(Boolean);
  const initials = nameParts.length > 1
    ? (nameParts[0][0] + nameParts[nameParts.length - 1][0]).toUpperCase()
    : (nameParts[0] ? nameParts[0].slice(0, 2).toUpperCase() : '?');
  if (avatarEl) avatarEl.textContent = initials;

  // Global navbar initials & name
  const navInitials = document.getElementById('user-avatar-initials');
  if (navInitials && initials !== '?') navInitials.textContent = initials;
  const navName = document.getElementById('user-full-name');
  if (navName && p.name) navName.textContent = p.name;

  // Candidate Name & Email
  const nameEl = document.getElementById('view-name');
  if (nameEl) nameEl.textContent = p.name || 'Candidate (Profile Not Set)';

  const emailEl = document.getElementById('view-email');
  if (emailEl) emailEl.textContent = p.email || '';

  // Pill Badges
  const roleBadge = document.getElementById('view-role-badge');
  if (roleBadge) {
    if (configured && t.role) {
      roleBadge.textContent = `Target: ${t.role}`;
      roleBadge.className = 'pill-badge badge-role';
    } else {
      roleBadge.textContent = 'Target: Not set';
      roleBadge.className = 'pill-badge badge-unset';
    }
  }

  const companyBadge = document.getElementById('view-company-badge');
  if (companyBadge) {
    if (configured && t.company) {
      companyBadge.textContent = `Company: ${t.company}`;
      companyBadge.className = 'pill-badge badge-company';
    } else {
      companyBadge.textContent = 'Company: Not set';
      companyBadge.className = 'pill-badge badge-unset';
    }
  }

  // 2-Column Metadata Grid
  const fullNameEl = document.getElementById('view-meta-fullname');
  if (fullNameEl) {
    fullNameEl.innerHTML = p.name ? p.name : '<span class="val-empty">— Not set yet</span>';
  }

  const eduEl = document.getElementById('view-meta-education');
  if (eduEl) {
    eduEl.innerHTML = (configured && p.education) ? p.education : '<span class="val-empty">— Not set yet</span>';
  }

  const expEl = document.getElementById('view-meta-experience');
  if (expEl) {
    expEl.innerHTML = (configured && p.experience_level) ? p.experience_level : '<span class="val-empty">— Not set yet</span>';
  }

  const targetRoleEl = document.getElementById('view-meta-role');
  if (targetRoleEl) {
    targetRoleEl.innerHTML = (configured && t.role) ? t.role : '<span class="val-empty">— Not set yet</span>';
  }

  const targetCompanyEl = document.getElementById('view-meta-company');
  if (targetCompanyEl) {
    targetCompanyEl.innerHTML = (configured && t.company) ? t.company : '<span class="val-empty">— Not set yet</span>';
  }



  // Technical Skills List
  const skillsCloud = document.getElementById('view-skills-cloud');
  if (skillsCloud) {
    skillsCloud.innerHTML = '';
    const skills = candidateProfile.skills || [];
    if (!configured || skills.length === 0) {
      skillsCloud.innerHTML = '<span class="val-empty">No skills added yet. Complete setup to add your skills.</span>';
    } else {
      skills.forEach(skill => {
        const span = document.createElement('span');
        span.className = 'skill-pill-item';
        span.textContent = skill;
        skillsCloud.appendChild(span);
      });
    }
  }
}

/**
 * Transition into Edit Mode Wizard
 */
function enterEditMode() {
  isEditing = true;
  currentStep = 0;

  const toggleBtn = document.getElementById('btn-mode-toggle');
  if (toggleBtn) {
    toggleBtn.innerHTML = 'Cancel';
    toggleBtn.classList.add('is-editing');
  }

  const viewCard = document.getElementById('profile-view-card');
  const wizardCard = document.getElementById('profile-wizard-card');
  if (viewCard) viewCard.style.display = 'none';
  if (wizardCard) wizardCard.style.display = 'block';

  // Populate Form Fields
  const configured = isProfileConfigured();
  const p = candidateProfile.personal || {};
  const t = candidateProfile.target || {};
  const pref = candidateProfile.preferences || {};

  const inputName = document.getElementById('input-name');
  if (inputName) {
    // If name not set in profile, use authenticated user's name if available
    const fallbackName = (window.api && window.api.getUser()) ? window.api.getUser().full_name : '';
    inputName.value = p.name || fallbackName || '';
  }

  const inputEdu = document.getElementById('input-education');
  if (inputEdu) {
    inputEdu.value = p.education || '';
  }

  const selectExp = document.getElementById('select-experience');
  if (selectExp) {
    selectExp.value = p.experience_level || '';
  }

  const selectRole = document.getElementById('select-role');
  if (selectRole) {
    selectRole.value = t.role || '';
  }

  const inputCompany = document.getElementById('input-company');
  if (inputCompany) {
    inputCompany.value = t.company || '';
  }

  currentSkills = Array.isArray(candidateProfile.skills) ? [...candidateProfile.skills] : [];
  renderSelectedSkills();
  renderSuggestionsList();



  hideErrorBanner();
  updateWizardUI();
}

/**
 * Exit Edit Mode without saving
 */
function exitEditMode() {
  isEditing = false;

  const viewCard = document.getElementById('profile-view-card');
  const wizardCard = document.getElementById('profile-wizard-card');
  if (viewCard) viewCard.style.display = 'block';
  if (wizardCard) wizardCard.style.display = 'none';

  hideErrorBanner();
  renderViewMode();
}

/**
 * Update wizard UI state
 */
function updateWizardUI() {
  const totalSteps = 3;
  const fillPercent = (currentStep / (totalSteps - 1)) * 100;
  const fillBar = document.getElementById('wizard-progress-fill');
  if (fillBar) {
    fillBar.style.width = `${fillPercent}%`;
  }

  document.querySelectorAll('.step-node').forEach(node => {
    const stepIdx = parseInt(node.getAttribute('data-step'), 10);
    const circle = node.querySelector('.step-circle');
    node.classList.remove('active', 'completed');

    if (stepIdx < currentStep) {
      node.classList.add('completed');
      if (circle) circle.textContent = '✓';
    } else if (stepIdx === currentStep) {
      node.classList.add('active');
      if (circle) circle.textContent = `${stepIdx + 1}`;
    } else {
      if (circle) circle.textContent = `${stepIdx + 1}`;
    }
  });

  // Toggle step panes
  document.querySelectorAll('.wizard-step-pane').forEach((pane, idx) => {
    if (idx === currentStep) {
      pane.classList.add('active');
    } else {
      pane.classList.remove('active');
    }
  });

  // Update Footer buttons
  const backBtn = document.getElementById('btn-wizard-back');
  if (backBtn) {
    if (currentStep === 0) {
      backBtn.classList.add('hidden');
    } else {
      backBtn.classList.remove('hidden');
    }
  }

  const continueBtn = document.getElementById('btn-wizard-continue');
  if (continueBtn) {
    if (currentStep === 2) {
      continueBtn.innerHTML = 'Submit Profile ✓';
      continueBtn.classList.add('btn-save');
    } else {
      continueBtn.innerHTML = 'Continue →';
      continueBtn.classList.remove('btn-save');
    }
  }
}

/**
 * Handle Back Button
 */
function handleWizardBack() {
  hideErrorBanner();
  if (currentStep > 0) {
    currentStep--;
    updateWizardUI();
  }
}

/**
 * Handle Continue or Save Button
 */
async function handleWizardContinue() {
  hideErrorBanner();

  if (!validateCurrentStep()) {
    return;
  }

  if (currentStep < 2) {
    currentStep++;
    updateWizardUI();
  } else {
    await saveProfileData();
  }
}

/**
 * Validate current step's inputs
 */
function validateCurrentStep() {
  if (currentStep === 0) {
    const name = (document.getElementById('input-name')?.value || '').trim();
    const education = (document.getElementById('input-education')?.value || '').trim();
    const exp = document.getElementById('select-experience')?.value;

    if (!name) {
      showErrorBanner('Please provide your Full Name to continue.');
      document.getElementById('input-name')?.focus();
      return false;
    }
    if (!education) {
      showErrorBanner('Please enter your Degree or Education background.');
      document.getElementById('input-education')?.focus();
      return false;
    }
    if (!exp) {
      showErrorBanner('Please select your Experience Tier.');
      document.getElementById('select-experience')?.focus();
      return false;
    }
  } else if (currentStep === 1) {
    const role = document.getElementById('select-role')?.value;
    if (!role) {
      showErrorBanner('Please select your Target Engineering Role.');
      document.getElementById('select-role')?.focus();
      return false;
    }
  } else if (currentStep === 2) {
    if (!currentSkills || currentSkills.length === 0) {
      showErrorBanner('Please add at least 1 technical skill or focus area to continue.');
      document.getElementById('skill-input')?.focus();
      return false;
    }
  }

  hideErrorBanner();
  return true;
}

/**
 * Add skill from input bar
 */
function addSkillFromInput() {
  const input = document.getElementById('skill-input');
  if (!input) return;
  const raw = input.value.trim();
  if (!raw) return;

  const exists = currentSkills.some(s => s.toLowerCase() === raw.toLowerCase());
  if (!exists) {
    currentSkills.push(raw);
    renderSelectedSkills();
    renderSuggestionsList();
  }

  input.value = '';
  input.focus();
  hideErrorBanner();
}

/**
 * Render selected skill pill tags with remove (✕) button
 */
function renderSelectedSkills() {
  const container = document.getElementById('selected-skills-container');
  if (!container) return;

  container.innerHTML = '';

  if (currentSkills.length === 0) {
    container.innerHTML = '<span class="empty-skills-placeholder">No skills selected yet. Add keywords above or tap quick suggestions.</span>';
    return;
  }

  currentSkills.forEach((skill, index) => {
    const tag = document.createElement('span');
    tag.className = 'skill-tag-badge';

    const text = document.createTextNode(skill);
    tag.appendChild(text);

    const removeBtn = document.createElement('button');
    removeBtn.className = 'skill-remove-btn';
    removeBtn.innerHTML = '&times;';
    removeBtn.setAttribute('title', `Remove ${skill}`);
    removeBtn.setAttribute('type', 'button');
    removeBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      removeSkillByIndex(index);
    });

    tag.appendChild(removeBtn);
    container.appendChild(tag);
  });
}

/**
 * Remove skill by index
 */
function removeSkillByIndex(index) {
  if (index >= 0 && index < currentSkills.length) {
    currentSkills.splice(index, 1);
    renderSelectedSkills();
    renderSuggestionsList();
  }
}

/**
 * Render Quick Suggestions (auto-hides items already selected)
 */
function renderSuggestionsList() {
  const listEl = document.getElementById('quick-suggestions-list');
  if (!listEl) return;

  listEl.innerHTML = '';

  const activeSkillsLower = currentSkills.map(s => s.toLowerCase());
  const available = DEFAULT_SUGGESTIONS.filter(item => !activeSkillsLower.includes(item.toLowerCase()));

  if (available.length === 0) {
    listEl.innerHTML = '<span style="font-size: 0.78rem; color: var(--color-text-muted); font-style: italic;">All quick suggestions added!</span>';
    return;
  }

  available.forEach(item => {
    const pill = document.createElement('button');
    pill.type = 'button';
    pill.className = 'btn-suggestion-pill';
    pill.textContent = `+ ${item}`;
    pill.addEventListener('click', () => {
      currentSkills.push(item);
      renderSelectedSkills();
      renderSuggestionsList();
      hideErrorBanner();
    });
    listEl.appendChild(pill);
  });
}



/**
 * Save and persist profile to localStorage and backend API
 */
async function saveProfileData() {
  const continueBtn = document.getElementById('btn-wizard-continue');
  const originalText = continueBtn ? continueBtn.innerHTML : 'Submit Profile ✓';
  if (continueBtn) {
    continueBtn.disabled = true;
    continueBtn.innerHTML = 'Saving... ⏳';
  }

  const nameVal = (document.getElementById('input-name')?.value || '').trim();
  const eduVal = (document.getElementById('input-education')?.value || '').trim();
  const expVal = document.getElementById('select-experience')?.value || '1–2 years';
  const roleVal = document.getElementById('select-role')?.value || 'Software Engineer';
  const companyVal = (document.getElementById('input-company')?.value || '').trim();

  const updatedProfile = {
    is_configured: true,
    personal: {
      name: nameVal,
      email: candidateProfile.personal.email || '',
      education: eduVal,
      experience_level: expVal
    },
    target: {
      role: roleVal,
      company: companyVal
    },
    skills: [...currentSkills],
    preferences: {
      input_mode: 'text',
      preferred_difficulty: 'Adaptive AI'
    }
  };

  // Persist locally
  candidateProfile = updatedProfile;
  localStorage.setItem(getUserProfileStorageKey(), JSON.stringify(candidateProfile));

  // Sync user in sessionStorage / localStorage so global navbar updates
  if (window.api) {
    const currentUser = window.api.getUser() || {};
    currentUser.full_name = nameVal;
    window.api.setAuthData({ user: currentUser });
  }

  // Persist to backend API if authenticated
  if (window.api && window.api.isAuthenticated()) {
    try {
      const res = await window.api.put('/auth/profile', updatedProfile);
      if (res.ok) {
        const savedData = await res.json();
        if (savedData && savedData.personal) {
          candidateProfile = savedData;
          candidateProfile.is_configured = true;
          localStorage.setItem(getUserProfileStorageKey(), JSON.stringify(candidateProfile));
        }
      }
    } catch (err) {
      console.warn('Could not sync profile to backend API:', err);
    }
  }

  if (continueBtn) {
    continueBtn.disabled = false;
    continueBtn.innerHTML = originalText;
  }

  // Transition back to View Mode
  exitEditMode();
  renderViewMode();

  // Show animated success banner
  showSuccessBanner('✨ Candidate profile updated successfully!');
}

/**
 * Show Success Banner
 */
function showSuccessBanner(message) {
  const banner = document.getElementById('profile-success-banner');
  const textEl = document.getElementById('success-banner-text');
  if (banner && textEl) {
    textEl.textContent = message;
    banner.style.display = 'flex';

    setTimeout(() => {
      dismissSuccessBanner();
    }, 4500);
  }
}

/**
 * Dismiss Success Banner
 */
function dismissSuccessBanner() {
  const banner = document.getElementById('profile-success-banner');
  if (banner) {
    banner.style.display = 'none';
  }
}

/**
 * Show Error Banner
 */
function showErrorBanner(message) {
  const banner = document.getElementById('profile-error-banner');
  const textEl = document.getElementById('error-banner-text');
  if (banner && textEl) {
    textEl.textContent = message;
    banner.style.display = 'flex';
    banner.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}

/**
 * Hide Error Banner
 */
function hideErrorBanner() {
  const banner = document.getElementById('profile-error-banner');
  if (banner) {
    banner.style.display = 'none';
  }
}

// Global helper functions
window.enterEditMode = enterEditMode;
window.dismissSuccessBanner = dismissSuccessBanner;
window.dismissErrorBanner = hideErrorBanner;
