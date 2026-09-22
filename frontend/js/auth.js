/**
 * Candidate Authentication Logic (Login & Register)
 */

document.addEventListener('DOMContentLoaded', () => {
  // If already authenticated, redirect to dashboard
  if (window.api && window.api.isAuthenticated()) {
    window.location.href = '/dashboard';
  }
});

function switchTab(tab) {
  const tabLogin = document.getElementById('tab-login');
  const tabRegister = document.getElementById('tab-register');
  const formLogin = document.getElementById('form-login');
  const formRegister = document.getElementById('form-register');

  if (tab === 'login') {
    tabLogin.classList.add('active');
    tabRegister.classList.remove('active');
    formLogin.classList.remove('hidden');
    formRegister.classList.add('hidden');
  } else {
    tabRegister.classList.add('active');
    tabLogin.classList.remove('active');
    formRegister.classList.remove('hidden');
    formLogin.classList.add('hidden');
  }
}

async function handleLogin(event) {
  event.preventDefault();
  const email = document.getElementById('login-email').value.trim();
  const password = document.getElementById('login-password').value;
  const btn = document.getElementById('btn-submit-login');

  if (!email || !password) {
    window.api.showToast('Please fill in all fields', 'error');
    return;
  }

  btn.disabled = true;
  btn.innerHTML = '<span>Signing in...</span>';

  try {
    const res = await window.api.post('/auth/login', { email, password });
    const data = await res.json();

    if (res.ok) {
      window.api.setAuthData(data);
      window.api.showToast(`Welcome back, ${data.user.full_name}!`, 'success');
      setTimeout(() => {
        window.location.href = '/dashboard';
      }, 700);
    } else {
      window.api.showToast(data.detail || 'Login failed. Please check your credentials.', 'error');
    }
  } catch (err) {
    window.api.showToast('Network error during login. Please try again.', 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span>Sign In to Dashboard</span><span class="arrow">→</span>';
  }
}

async function handleRegister(event) {
  event.preventDefault();
  const fullName = document.getElementById('reg-fullname').value.trim();
  const email = document.getElementById('reg-email').value.trim();
  const password = document.getElementById('reg-password').value;
  const btn = document.getElementById('btn-submit-register');

  if (!fullName || !email || !password) {
    window.api.showToast('Please complete all fields', 'error');
    return;
  }

  if (password.length < 6) {
    window.api.showToast('Password must be at least 6 characters', 'error');
    return;
  }

  btn.disabled = true;
  btn.innerHTML = '<span>Creating account...</span>';

  try {
    const res = await window.api.post('/auth/register', {
      full_name: fullName,
      email: email,
      password: password
    });
    const data = await res.json();

    if (res.ok) {
      window.api.setAuthData(data);
      window.api.showToast(`Account created! Welcome, ${data.user.full_name}!`, 'success');
      setTimeout(() => {
        window.location.href = '/dashboard';
      }, 700);
    } else {
      window.api.showToast(data.detail || 'Registration failed.', 'error');
    }
  } catch (err) {
    window.api.showToast('Network error during registration.', 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span>Create Candidate Account</span><span class="arrow">→</span>';
  }
}
