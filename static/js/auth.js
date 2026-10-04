/**
 * QUIZNOVA – AUTHENTICATION JAVASCRIPT
 * Handles Login, Registration, Demo Credentials, and Form Validation
 */

document.addEventListener('DOMContentLoaded', () => {
  // If already logged in, redirect away from login/register
  if (Auth.isLoggedIn()) {
    const user = Auth.getUser();
    if (window.location.pathname.includes('login') || window.location.pathname.includes('register')) {
      if (user && user.role === 'ADMIN') {
        window.location.href = '/admin.html';
      } else {
        window.location.href = '/dashboard.html';
      }
      return;
    }
  }

  // Login Form
  const loginForm = document.getElementById('login-form');
  if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const submitBtn = loginForm.querySelector('button[type="submit"]');
      const originalText = submitBtn.innerHTML;

      const email = document.getElementById('login-email').value.trim();
      const password = document.getElementById('login-password').value;

      if (!email || !password) {
        showToast('Missing Fields', 'Please enter both email and password.', 'warning');
        return;
      }

      try {
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<span class="spinner"></span> Signing in...`;

        const data = await apiFetch('/api/auth/login', {
          method: 'POST',
          body: { email, password }
        });

        Auth.setToken(data.access_token);
        Auth.setUser(data.user);

        showToast('Welcome Back!', `Signed in as ${data.user.name}`, 'success');

        const params = new URLSearchParams(window.location.search);
        const redirectUrl = params.get('redirect');

        setTimeout(() => {
          if (redirectUrl) {
            window.location.href = redirectUrl;
          } else if (data.user.role === 'ADMIN') {
            window.location.href = '/admin.html';
          } else {
            window.location.href = '/dashboard.html';
          }
        }, 600);
      } catch (err) {
        showToast('Login Failed', err.message || 'Invalid credentials.', 'error');
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
      }
    });
  }

  // Register Form
  const registerForm = document.getElementById('register-form');
  if (registerForm) {
    registerForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const submitBtn = registerForm.querySelector('button[type="submit"]');
      const originalText = submitBtn.innerHTML;

      const name = document.getElementById('reg-name').value.trim();
      const email = document.getElementById('reg-email').value.trim();
      const password = document.getElementById('reg-password').value;
      const confirmPassword = document.getElementById('reg-confirm-password').value;
      const role = document.getElementById('reg-role') ? document.getElementById('reg-role').value : 'STUDENT';

      if (!name || !email || !password || !confirmPassword) {
        showToast('Missing Fields', 'Please complete all required fields.', 'warning');
        return;
      }

      if (password !== confirmPassword) {
        showToast('Password Mismatch', 'Password and confirmation do not match.', 'error');
        return;
      }

      if (password.length < 6) {
        showToast('Weak Password', 'Password must be at least 6 characters long.', 'warning');
        return;
      }

      try {
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<span class="spinner"></span> Creating Account...`;

        const data = await apiFetch('/api/auth/register', {
          method: 'POST',
          body: {
            name,
            email,
            password,
            confirm_password: confirmPassword,
            role
          }
        });

        Auth.setToken(data.access_token);
        Auth.setUser(data.user);

        showToast('Account Created!', 'Welcome to QuizNova!', 'success');

        setTimeout(() => {
          if (data.user.role === 'ADMIN') {
            window.location.href = '/admin.html';
          } else {
            window.location.href = '/dashboard.html';
          }
        }, 700);
      } catch (err) {
        showToast('Registration Error', err.message || 'Could not complete registration.', 'error');
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
      }
    });
  }

  // Password Visibility Toggle
  document.querySelectorAll('.password-toggle-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-target');
      const input = document.getElementById(targetId);
      if (input) {
        const isPassword = input.type === 'password';
        input.type = isPassword ? 'text' : 'password';
        btn.innerHTML = isPassword ? `<i class="fa-solid fa-eye-slash"></i>` : `<i class="fa-solid fa-eye"></i>`;
      }
    });
  });
});

// Demo Account Helpers
function fillDemoStudent() {
  return demoLogin('STUDENT', 'demo-student-login');
}

function fillDemoAdmin() {
  return demoLogin('ADMIN', 'demo-admin-login');
}

async function demoLogin(role, buttonId) {
  const button = document.getElementById(buttonId);
  if (!button) return;

  const originalText = button.innerHTML;
  button.disabled = true;
  button.innerHTML = `<span class="spinner"></span> Signing in...`;

  try {
    const data = await apiFetch('/api/auth/demo-login', {
      method: 'POST',
      body: { role }
    });

    Auth.setToken(data.access_token);
    Auth.setUser(data.user);
    showToast('Welcome to QuizNova!', `Signed in as ${data.user.name}`, 'success');

    setTimeout(() => {
      window.location.href = data.user.role === 'ADMIN' ? '/admin.html' : '/dashboard.html';
    }, 600);
  } catch (err) {
    showToast('Demo Login Failed', err.message || 'Could not sign in to the demo account.', 'error');
    button.disabled = false;
    button.innerHTML = originalText;
  }
}
