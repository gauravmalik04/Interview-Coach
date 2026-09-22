/**
 * AI Interview Platform — Frontend API & Auth Client
 * Handles JWT Bearer attachment, transparent token refresh, and toast alerts.
 */

class ApiClient {
  constructor(baseUrl = '') {
    this.baseUrl = baseUrl;
    this.tokenKey = 'ai_interview_access_token';
    this.refreshKey = 'ai_interview_refresh_token';
    this.userKey = 'ai_interview_user';
    this.hydrateSession();
  }

  hydrateSession() {
    try {
      // Sync from localStorage to sessionStorage if missing in current tab
      const localToken = localStorage.getItem(this.tokenKey);
      const sessionToken = sessionStorage.getItem(this.tokenKey);
      if (!sessionToken && localToken) {
        sessionStorage.setItem(this.tokenKey, localToken);
      } else if (sessionToken && !localToken) {
        localStorage.setItem(this.tokenKey, sessionToken);
      }

      const localRefresh = localStorage.getItem(this.refreshKey);
      const sessionRefresh = sessionStorage.getItem(this.refreshKey);
      if (!sessionRefresh && localRefresh) {
        sessionStorage.setItem(this.refreshKey, localRefresh);
      } else if (sessionRefresh && !localRefresh) {
        localStorage.setItem(this.refreshKey, sessionRefresh);
      }

      const localUser = localStorage.getItem(this.userKey);
      const sessionUser = sessionStorage.getItem(this.userKey);
      if (!sessionUser && localUser) {
        sessionStorage.setItem(this.userKey, localUser);
      } else if (sessionUser && !localUser) {
        localStorage.setItem(this.userKey, sessionUser);
      }
    } catch (e) {
      console.warn('Storage sync error:', e);
    }
  }

  getAccessToken() {
    return sessionStorage.getItem(this.tokenKey) || localStorage.getItem(this.tokenKey);
  }

  getRefreshToken() {
    return sessionStorage.getItem(this.refreshKey) || localStorage.getItem(this.refreshKey);
  }

  getUser() {
    const raw = sessionStorage.getItem(this.userKey) || localStorage.getItem(this.userKey);
    try {
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }

  setAuthData(data) {
    if (!data) return;

    if (data.access_token) {
      sessionStorage.setItem(this.tokenKey, data.access_token);
      localStorage.setItem(this.tokenKey, data.access_token);
    }
    if (data.refresh_token) {
      sessionStorage.setItem(this.refreshKey, data.refresh_token);
      localStorage.setItem(this.refreshKey, data.refresh_token);
    }
    if (data.user) {
      const userStr = typeof data.user === 'string' ? data.user : JSON.stringify(data.user);
      sessionStorage.setItem(this.userKey, userStr);
      localStorage.setItem(this.userKey, userStr);
    }
  }

  clearAuth() {
    sessionStorage.removeItem(this.tokenKey);
    sessionStorage.removeItem(this.refreshKey);
    sessionStorage.removeItem(this.userKey);
    localStorage.removeItem(this.tokenKey);
    localStorage.removeItem(this.refreshKey);
    localStorage.removeItem(this.userKey);
  }

  isAuthenticated() {
    return !!(this.getAccessToken() || this.getRefreshToken());
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    options.headers = options.headers || {};

    // If no access token but refresh token exists, attempt refresh first
    let token = this.getAccessToken();
    if (!token && this.getRefreshToken()) {
      await this.refreshToken();
      token = this.getAccessToken();
    }

    // Attach Bearer token if present
    if (token) {
      options.headers['Authorization'] = `Bearer ${token}`;
    }

    if (!(options.body instanceof FormData) && !options.headers['Content-Type']) {
      options.headers['Content-Type'] = 'application/json';
    }

    let response = await fetch(url, options);

    // If 401 Unauthorized, attempt refresh once
    if (response.status === 401 && this.getRefreshToken()) {
      const refreshed = await this.refreshToken();
      if (refreshed) {
        options.headers['Authorization'] = `Bearer ${this.getAccessToken()}`;
        response = await fetch(url, options);
      } else {
        this.clearAuth();
        window.location.href = '/';
      }
    }

    return response;
  }

  async refreshToken() {
    const refreshToken = this.getRefreshToken();
    if (!refreshToken) return false;

    try {
      const res = await fetch(`${this.baseUrl}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken })
      });

      if (res.ok) {
        const data = await res.json();
        this.setAuthData(data);
        return true;
      }
      return false;
    } catch {
      return false;
    }
  }

  async get(endpoint) {
    const res = await this.request(endpoint, { method: 'GET' });
    return res;
  }

  async post(endpoint, data = {}) {
    const res = await this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(data)
    });
    return res;
  }

  async put(endpoint, data = {}) {
    const res = await this.request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data)
    });
    return res;
  }

  async patch(endpoint, data = {}) {
    const res = await this.request(endpoint, {
      method: 'PATCH',
      body: JSON.stringify(data)
    });
    return res;
  }

  async delete(endpoint) {
    const res = await this.request(endpoint, {
      method: 'DELETE'
    });
    return res;
  }

  showToast(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(100%)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }
}

// Global API instance
window.api = new ApiClient();

/**
 * Global handler for the navbar "Interview" tab:
 * Checks for any active resumable interview (coached mode).
 * If active interview exists -> resumes it (/interview?session_id=...).
 * If no active interview exists -> redirects or stays on /dashboard.
 */
async function handleNavInterviewClick(e) {
  if (e && typeof e.preventDefault === 'function') {
    e.preventDefault();
  }

  if (!window.api.isAuthenticated()) {
    window.api.showToast('Please log in to access the interview room.', 'info');
    setTimeout(() => { window.location.href = '/'; }, 800);
    return;
  }

  try {
    const res = await window.api.get('/sessions/active');
    if (res.ok) {
      const data = await res.json();
      if (data && data.has_active && data.session_id) {
        window.location.href = `/interview?session_id=${data.session_id}`;
        return;
      }
    }
  } catch (err) {
    console.error('Active interview check failed:', err);
  }

  window.api.showToast('No active interview in progress. Start a session from the dashboard!', 'info');
  if (window.location.pathname !== '/dashboard') {
    setTimeout(() => { window.location.href = '/dashboard'; }, 800);
  }
}

// Automatically attach handler to navbar interview links upon DOM load
if (typeof document !== 'undefined') {
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('a[href="/interview"]').forEach(link => {
      const href = link.getAttribute('href');
      if (href === '/interview' || href === '/interview/') {
        link.addEventListener('click', handleNavInterviewClick);
      }
    });
  });
}
