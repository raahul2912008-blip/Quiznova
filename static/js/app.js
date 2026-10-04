/**
 * QUIZNOVA – MASTER APPLICATION JAVASCRIPT
 * Handles Auth Tokens, Educational Theme System, API Client, Toast System, Modals,
 * and the Floating AI Learning Assistant Widget
 */

const API_BASE = '';

// ==========================================
// THEME MANAGEMENT (NAVY / LIGHT)
// ==========================================
const ThemeManager = {
  themes: ['light', 'navy'],
  labels: {
    navy: '🌙 Navy',
    light: '☀️ Paper'
  },

  getTheme() {
    const savedTheme = localStorage.getItem('quiznova_theme');
    const hasUpdatedPreference = localStorage.getItem('quiznova_theme_v2') === 'true';
    return hasUpdatedPreference ? savedTheme || 'light' : 'light';
  },

  setTheme(theme) {
    if (!this.themes.includes(theme)) theme = 'light';
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('quiznova_theme', theme);
    localStorage.setItem('quiznova_theme_v2', 'true');

    const labelEl = document.getElementById('theme-toggle-label');
    if (labelEl) {
      labelEl.textContent = this.labels[theme];
    }
  },

  cycleTheme() {
    const current = this.getTheme();
    const currentIndex = this.themes.indexOf(current);
    const nextIndex = (currentIndex + 1) % this.themes.length;
    const nextTheme = this.themes[nextIndex];
    this.setTheme(nextTheme);
    showToast('Theme Changed', `Switched to ${nextTheme === 'navy' ? 'Deep Navy' : 'Paper Light'} Mode`, 'info', 1800);
  },

  init() {
    this.setTheme(this.getTheme());
  }
};

// Initialize theme immediately to prevent flashing
ThemeManager.init();

// ==========================================
// AUTH & TOKEN MANAGEMENT
// ==========================================
const Auth = {
  getToken() {
    return localStorage.getItem('quiznova_token');
  },

  setToken(token) {
    localStorage.setItem('quiznova_token', token);
  },

  getUser() {
    const u = localStorage.getItem('quiznova_user');
    try {
      return u ? JSON.parse(u) : null;
    } catch {
      return null;
    }
  },

  setUser(user) {
    localStorage.setItem('quiznova_user', JSON.stringify(user));
  },

  isLoggedIn() {
    return !!this.getToken();
  },

  isAdmin() {
    const user = this.getUser();
    return user && user.role === 'ADMIN';
  },

  logout() {
    localStorage.removeItem('quiznova_token');
    localStorage.removeItem('quiznova_user');
    showToast('Signed Out', 'You have been signed out. See you next time!', 'info');
    setTimeout(() => {
      window.location.href = '/login.html';
    }, 450);
  },

  requireAuth() {
    if (!this.isLoggedIn()) {
      showToast('Welcome to QuizNova', 'Please sign in to access your learning portal.', 'warning');
      setTimeout(() => {
        window.location.href = `/login.html?redirect=${encodeURIComponent(window.location.pathname)}`;
      }, 500);
      return false;
    }
    return true;
  },

  requireAdmin() {
    if (!this.requireAuth()) return false;
    if (!this.isAdmin()) {
      showToast('Instructor Area', 'Instructor or administrator privileges are required.', 'error');
      setTimeout(() => {
        window.location.href = '/dashboard.html';
      }, 500);
      return false;
    }
    return true;
  }
};

// ==========================================
// API CLIENT
// ==========================================
async function apiFetch(endpoint, options = {}) {
  const headers = options.headers || {};
  const token = Auth.getToken();

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(options.body);
  }

  options.headers = headers;

  try {
    const response = await fetch(`${API_BASE}${endpoint}`, options);

    if (response.status === 401) {
      if (!window.location.pathname.includes('login') && !window.location.pathname.includes('register')) {
        Auth.logout();
      }
      const data = await response.json().catch(() => ({ detail: 'Unauthorized' }));
      throw new Error(data.detail || 'Session expired. Please log in.');
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: `HTTP error ${response.status}` }));
      throw new Error(errorData.detail || errorData.message || `Request failed with status ${response.status}`);
    }

    return await response.json();
  } catch (err) {
    throw err;
  }
}

// ==========================================
// TOAST NOTIFICATION SYSTEM
// ==========================================
function getOrCreateToastContainer() {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }
  return container;
}

function showToast(title, message, type = 'info', duration = 3500) {
  const container = getOrCreateToastContainer();

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;

  const iconMap = {
    success: 'fa-solid fa-circle-check',
    error: 'fa-solid fa-triangle-exclamation',
    warning: 'fa-solid fa-circle-exclamation',
    info: 'fa-solid fa-circle-info'
  };

  const iconClass = iconMap[type] || iconMap.info;

  toast.innerHTML = `
    <i class="${iconClass} toast-icon"></i>
    <div class="toast-content">
      <div class="toast-title">${escapeHtml(title)}</div>
      <div class="toast-msg">${escapeHtml(message)}</div>
    </div>
    <button class="toast-close" onclick="this.parentElement.remove()">&times;</button>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    setTimeout(() => toast.remove(), 250);
  }, duration);
}

// ==========================================
// CONFIRMATION MODAL SYSTEM
// ==========================================
function showConfirmModal({ title, message, confirmText = 'Confirm', cancelText = 'Cancel', confirmClass = 'btn-primary', onConfirm }) {
  let overlay = document.getElementById('global-confirm-modal');
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.id = 'global-confirm-modal';
    overlay.className = 'modal-overlay';
    document.body.appendChild(overlay);
  }

  overlay.innerHTML = `
    <div class="modal-card">
      <div class="modal-icon-badge" style="background: rgba(59, 130, 246, 0.12); color: var(--accent-primary);">
        <i class="fa-solid fa-circle-question"></i>
      </div>
      <h3 style="font-size: 1.25rem; margin-bottom: 0.4rem;">${escapeHtml(title)}</h3>
      <p style="color: var(--text-muted); font-size: 0.92rem; line-height: 1.5;">${escapeHtml(message)}</p>
      <div class="modal-actions">
        <button id="modal-cancel-btn" class="btn btn-secondary">${escapeHtml(cancelText)}</button>
        <button id="modal-confirm-btn" class="btn ${confirmClass}">${escapeHtml(confirmText)}</button>
      </div>
    </div>
  `;

  overlay.classList.add('active');

  const close = () => {
    overlay.classList.remove('active');
  };

  document.getElementById('modal-cancel-btn').onclick = close;
  document.getElementById('modal-confirm-btn').onclick = () => {
    close();
    if (typeof onConfirm === 'function') onConfirm();
  };

  overlay.onclick = (e) => {
    if (e.target === overlay) close();
  };
}

// ==========================================
// UI & NAVBAR INITIALIZATION
// ==========================================
function initNavbar() {
  const authContainer = document.getElementById('nav-auth-section');
  if (!authContainer) return;

  const currentTheme = ThemeManager.getTheme();
  const themeLabel = ThemeManager.labels[currentTheme] || '☀️ Paper';

  const themeButtonHtml = `
    <button class="theme-toggle-btn" id="theme-toggle-btn" onclick="ThemeManager.cycleTheme()" title="Switch Color Theme">
      <span id="theme-toggle-label">${themeLabel}</span>
    </button>
  `;

  const user = Auth.getUser();

  if (user) {
    const initials = user.name
      .split(' ')
      .map(n => n[0])
      .join('')
      .substring(0, 2)
      .toUpperCase();

    const roleBadge = user.role === 'ADMIN'
      ? `<span class="badge badge-purple" style="font-size: 0.65rem;">INSTRUCTOR</span>`
      : `<span class="badge badge-blue" style="font-size: 0.65rem;">STUDENT</span>`;

    authContainer.innerHTML = `
      ${themeButtonHtml}
      <div class="nav-user-dropdown">
        <button class="user-badge-btn" id="user-menu-trigger">
          <div class="user-avatar-circle">${initials}</div>
          <span>${escapeHtml(user.name.split(' ')[0])}</span>
          ${roleBadge}
          <i class="fa-solid fa-chevron-down" style="font-size: 0.72rem; color: var(--text-muted);"></i>
        </button>
        <div class="dropdown-menu" id="user-menu-dropdown">
          ${user.role === 'ADMIN' ? `
            <a href="/admin.html" class="dropdown-item"><i class="fa-solid fa-chart-line"></i> Admin Panel</a>
            <a href="/create-quiz.html" class="dropdown-item"><i class="fa-solid fa-circle-plus"></i> Create Quiz</a>
            <a href="/manage-quizzes.html" class="dropdown-item"><i class="fa-solid fa-sliders"></i> Manage Quizzes</a>
            <a href="/results.html" class="dropdown-item"><i class="fa-solid fa-list-check"></i> Submissions</a>
          ` : `
            <a href="/dashboard.html" class="dropdown-item"><i class="fa-solid fa-shapes"></i> My Dashboard</a>
            <a href="/leaderboard.html" class="dropdown-item"><i class="fa-solid fa-trophy"></i> Leaderboard</a>
            <a href="/profile.html" class="dropdown-item"><i class="fa-solid fa-user"></i> My Profile</a>
          `}
          <hr style="border: none; border-top: 1px solid var(--border-glass-light); margin: 3px 0;">
          <a href="javascript:void(0)" class="dropdown-item" id="logout-btn" style="color: var(--accent-rose);">
            <i class="fa-solid fa-arrow-right-from-bracket"></i> Sign Out
          </a>
        </div>
      </div>
    `;

    const trigger = document.getElementById('user-menu-trigger');
    const dropdown = document.getElementById('user-menu-dropdown');
    const logoutBtn = document.getElementById('logout-btn');

    if (trigger && dropdown) {
      trigger.onclick = (e) => {
        e.stopPropagation();
        dropdown.classList.toggle('show');
      };

      document.addEventListener('click', () => {
        dropdown.classList.remove('show');
      });
    }

    if (logoutBtn) {
      logoutBtn.onclick = () => Auth.logout();
    }
  } else {
    authContainer.innerHTML = `
      ${themeButtonHtml}
      <a href="/login.html" class="btn btn-secondary btn-sm">Sign In</a>
      <a href="/register.html" class="btn btn-primary btn-sm">Join Free</a>
    `;
  }

  // Mobile sidebar toggle handler
  const mobileMenuBtn = document.getElementById('mobile-menu-btn');
  const sidebar = document.querySelector('.sidebar');
  if (mobileMenuBtn && sidebar) {
    let backdrop = document.getElementById('sidebar-backdrop');
    if (!backdrop) {
      backdrop = document.createElement('div');
      backdrop.id = 'sidebar-backdrop';
      backdrop.className = 'sidebar-backdrop';
      document.body.appendChild(backdrop);
    }

    const toggleSidebar = () => {
      sidebar.classList.toggle('mobile-open');
      backdrop.classList.toggle('active');
    };

    const closeSidebar = () => {
      sidebar.classList.remove('mobile-open');
      backdrop.classList.remove('active');
    };

    mobileMenuBtn.onclick = toggleSidebar;
    backdrop.onclick = closeSidebar;

    sidebar.querySelectorAll('.sidebar-item').forEach(item => {
      item.addEventListener('click', closeSidebar);
    });
  }
}

// ==========================================
// FLOATING AI LEARNING ASSISTANT WIDGET
// ==========================================
const AIAssistantWidget = {
  isOpen: false,

  init() {
    if (document.getElementById('ai-fab-wrapper')) return;

    const user = Auth.getUser();
    const firstName = user && user.name ? user.name.split(' ')[0] : 'there';

    const fabContainer = document.createElement('div');
    fabContainer.id = 'ai-fab-wrapper';
    fabContainer.className = 'ai-fab-container';

    fabContainer.innerHTML = `
      <div class="ai-fab-tooltip">Need help? Ask QuizNova AI</div>
      <button class="ai-fab-btn" id="ai-fab-toggle-btn" aria-label="Open AI Learning Assistant">
        <i class="fa-solid fa-graduation-cap"></i>
        <span class="ai-fab-pulse"></span>
      </button>

      <!-- Chat Window -->
      <div class="ai-chat-window" id="ai-chat-box">
        <div class="ai-chat-header">
          <div class="ai-header-info">
            <div class="ai-avatar">
              <i class="fa-solid fa-graduation-cap"></i>
            </div>
            <div>
              <div class="ai-header-title">QuizNova AI</div>
              <div class="ai-header-sub"><i class="fa-solid fa-circle" style="font-size: 0.5rem;"></i> Your learning assistant &bull; Online</div>
            </div>
          </div>
          <button class="ai-chat-close" id="ai-chat-close-btn" aria-label="Close Assistant">&times;</button>
        </div>

        <div class="ai-chat-messages" id="ai-chat-messages-body">
          <div class="ai-msg assistant">
            <div class="ai-msg-bubble">
              Hi ${escapeHtml(firstName)}! 👋 I'm QuizNova AI, your personal learning guide. How can I help you find your way around QuizNova today?
            </div>
          </div>
        </div>

        <div class="ai-suggestions-row" id="ai-suggestions-container">
          <span class="ai-suggestion-pill" data-query="Where are my quizzes?">📚 Where are my quizzes?</span>
          <span class="ai-suggestion-pill" data-query="How do I start a quiz?">🚀 How do I start a quiz?</span>
          <span class="ai-suggestion-pill" data-query="How do I see my results?">📊 See my results</span>
          <span class="ai-suggestion-pill" data-query="Where is the leaderboard?">🏆 Leaderboard</span>
          <span class="ai-suggestion-pill" data-query="Where can I see my profile?">👤 My Profile</span>
          <span class="ai-suggestion-pill" data-query="What does my score mean?">💡 Score meaning</span>
          <span class="ai-suggestion-pill" data-query="How does the timer work?">⏱️ Timer info</span>
          <span class="ai-suggestion-pill" data-query="How do I submit a quiz?">📝 Submit quiz</span>
          <span class="ai-suggestion-pill" data-query="Can I retake a quiz?">🔄 Retake quiz</span>
          <span class="ai-suggestion-pill" data-query="How do I track my streak?">🔥 Learning Streak</span>
        </div>

        <div class="ai-chat-input-wrapper">
          <input type="text" class="ai-chat-input" id="ai-user-input" placeholder="Ask me anything about QuizNova..." autocomplete="off">
          <button class="ai-send-btn" id="ai-send-btn" aria-label="Send message">
            <i class="fa-solid fa-paper-plane"></i>
          </button>
        </div>
      </div>
    `;

    document.body.appendChild(fabContainer);

    // Event Listeners
    const fabBtn = document.getElementById('ai-fab-toggle-btn');
    const closeBtn = document.getElementById('ai-chat-close-btn');
    const chatBox = document.getElementById('ai-chat-box');
    const input = document.getElementById('ai-user-input');
    const sendBtn = document.getElementById('ai-send-btn');
    const suggestions = document.querySelectorAll('.ai-suggestion-pill');

    const toggleChat = () => {
      this.isOpen = !this.isOpen;
      chatBox.classList.toggle('open', this.isOpen);
      if (this.isOpen) {
        input.focus();
      }
    };

    fabBtn.onclick = toggleChat;
    closeBtn.onclick = () => {
      this.isOpen = false;
      chatBox.classList.remove('open');
    };

    const handleSend = () => {
      const text = input.value.trim();
      if (!text) return;
      this.sendMessage(text);
      input.value = '';
    };

    sendBtn.onclick = handleSend;
    input.onkeydown = (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        handleSend();
      }
    };

    suggestions.forEach(pill => {
      pill.onclick = () => {
        const query = pill.getAttribute('data-query');
        this.sendMessage(query);
      };
    });
  },

  async sendMessage(text) {
    const messagesBody = document.getElementById('ai-chat-messages-body');
    if (!messagesBody) return;

    // 1. Append User Message
    const userMsgEl = document.createElement('div');
    userMsgEl.className = 'ai-msg user';
    userMsgEl.innerHTML = `<div class="ai-msg-bubble">${escapeHtml(text)}</div>`;
    messagesBody.appendChild(userMsgEl);
    messagesBody.scrollTop = messagesBody.scrollHeight;

    // 2. Append Typing Indicator
    const typingEl = document.createElement('div');
    typingEl.className = 'ai-msg assistant';
    typingEl.id = 'ai-typing-indicator';
    typingEl.innerHTML = `
      <div class="ai-msg-bubble">
        <div class="ai-typing-indicator">
          <span class="ai-typing-dot"></span>
          <span class="ai-typing-dot"></span>
          <span class="ai-typing-dot"></span>
          <span style="font-size: 0.76rem; color: var(--text-muted); margin-left: 6px;">QuizNova AI is typing...</span>
        </div>
      </div>
    `;
    messagesBody.appendChild(typingEl);
    messagesBody.scrollTop = messagesBody.scrollHeight;

    // 3. Fetch from API or fallback
    try {
      const data = await apiFetch('/api/ai-assistant', {
        method: 'POST',
        body: { message: text }
      });

      typingEl.remove();
      this.appendAssistantMessage(data.reply, data.actions || []);
    } catch (err) {
      typingEl.remove();
      // Reliable fallback matching
      const fallback = this.getFallbackResponse(text);
      this.appendAssistantMessage(fallback.reply, fallback.actions);
    }
  },

  appendAssistantMessage(replyText, actions = []) {
    const messagesBody = document.getElementById('ai-chat-messages-body');
    if (!messagesBody) return;

    const astMsgEl = document.createElement('div');
    astMsgEl.className = 'ai-msg assistant';

    let actionsHtml = '';
    if (actions && actions.length > 0) {
      actionsHtml = `
        <div class="ai-actions-container">
          ${actions.map(act => `
            <a href="${act.url}" class="ai-action-chip">
              <i class="${act.icon || 'fa-solid fa-arrow-right'}"></i>
              ${escapeHtml(act.label)}
            </a>
          `).join('')}
        </div>
      `;
    }

    // Convert bold markdown **text** to <strong>
    const formattedReply = escapeHtml(replyText).replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    astMsgEl.innerHTML = `
      <div class="ai-msg-bubble">
        ${formattedReply}
        ${actionsHtml}
      </div>
    `;

    messagesBody.appendChild(astMsgEl);
    messagesBody.scrollTop = messagesBody.scrollHeight;
  },

  getFallbackResponse(query) {
    const q = query.toLowerCase();

    if (q.includes('where') && (q.includes('quiz') || q.includes('find') || q.includes('explore'))) {
      return {
        reply: "You can find all available quizzes by clicking **Explore Quizzes** in the left sidebar or scrolling to the quizzes section on your dashboard.\n\n📍 **Navigation Path:** Dashboard → Explore Quizzes → Select Quiz → Start Learning",
        actions: [
          { label: "Explore Quizzes", url: "/dashboard.html#available-quizzes-section", icon: "fa-solid fa-book-open" },
          { label: "Go to Dashboard", url: "/dashboard.html", icon: "fa-solid fa-house" }
        ]
      };
    }

    if (q.includes('start') || q.includes('begin') || q.includes('play') || q.includes('take a quiz')) {
      return {
        reply: "Starting a quiz is simple! Head to **Explore Quizzes**, choose any subject you'd like to practice today, and click **Start Learning**.\n\n📍 **Navigation Path:** Dashboard → Explore Quizzes → Pick Topic → Click 'Start Learning'",
        actions: [
          { label: "Choose a Quiz", url: "/dashboard.html#available-quizzes-section", icon: "fa-solid fa-play" },
          { label: "Go to Dashboard", url: "/dashboard.html", icon: "fa-solid fa-house" }
        ]
      };
    }

    if (q.includes('result') || q.includes('score') || q.includes('grade') || q.includes('past')) {
      return {
        reply: "After submitting any quiz, your result appears immediately with your score percentage, time spent, and answer explanations. You can also view all your previous results under **My Progress** in the left sidebar.\n\n📍 **Navigation Path:** Dashboard → Left Sidebar → My Progress",
        actions: [
          { label: "View My Results", url: "/profile.html", icon: "fa-solid fa-chart-line" },
          { label: "Go to Dashboard", url: "/dashboard.html", icon: "fa-solid fa-house" }
        ]
      };
    }

    if (q.includes('leaderboard') || q.includes('rank') || q.includes('podium') || q.includes('standing')) {
      return {
        reply: "The **Leaderboard** ranks students based on highest score percentage and completion speed. The Top 3 achievers are featured on the Gold, Silver, and Bronze podium cards!\n\n📍 **Navigation Path:** Top Navigation (or Left Sidebar) → Leaderboard",
        actions: [
          { label: "Open Leaderboard", url: "/leaderboard.html", icon: "fa-solid fa-trophy" },
          { label: "Go to Dashboard", url: "/dashboard.html", icon: "fa-solid fa-house" }
        ]
      };
    }

    if (q.includes('profile') || q.includes('account') || q.includes('my details')) {
      return {
        reply: "Your **Profile** displays your student account information, learning streak, overall average score, personal best, and complete past quiz history.\n\n📍 **Navigation Path:** Left Sidebar → My Profile",
        actions: [
          { label: "Open Profile", url: "/profile.html", icon: "fa-solid fa-user" },
          { label: "Go to Dashboard", url: "/dashboard.html", icon: "fa-solid fa-house" }
        ]
      };
    }

    if (q.includes('timer') || q.includes('time') || q.includes('countdown') || q.includes('expire')) {
      return {
        reply: "Each quiz has an estimated time limit shown on its card. A live countdown displays in the top bar. Under 60 seconds, it flashes a friendly warning. At 00:00, your answers are submitted automatically so nothing is lost!",
        actions: [{ label: "Explore Quizzes", url: "/dashboard.html#available-quizzes-section", icon: "fa-solid fa-play" }]
      };
    }

    if (q.includes('retake') || q.includes('try again') || q.includes('retry') || q.includes('repeat')) {
      return {
        reply: "Yes! QuizNova encourages unlimited practice. You can retake any quiz as many times as you like. Your best score will be recorded on your profile.\n\n📍 **Navigation Path:** Dashboard → Continue Learning / Explore Quizzes → Click 'Practice Again'",
        actions: [{ label: "Explore Quizzes", url: "/dashboard.html#available-quizzes-section", icon: "fa-solid fa-rotate-right" }]
      };
    }

    if (q.includes('streak') || q.includes('goal')) {
      return {
        reply: "Your **Learning Streak** tracks consecutive active days of completing quizzes. Your **Weekly Goal** challenges you to complete 3 quizzes every week. Track both on your dashboard and left sidebar!\n\n📍 **Navigation Path:** Dashboard → Welcome Header & Sidebar Goal Widget",
        actions: [
          { label: "Go to Dashboard", url: "/dashboard.html", icon: "fa-solid fa-house" },
          { label: "View My Progress", url: "/profile.html", icon: "fa-solid fa-chart-line" }
        ]
      };
    }

    return {
      reply: "I'm here to support your learning journey on QuizNova! You can ask me how to start or submit quizzes, where to find your past results, how scoring and the timer work, or where to view the leaderboard.",
      actions: [
        { label: "Explore Quizzes", url: "/dashboard.html#available-quizzes-section", icon: "fa-solid fa-book-open" },
        { label: "Leaderboard", url: "/leaderboard.html", icon: "fa-solid fa-trophy" },
        { label: "My Profile", url: "/profile.html", icon: "fa-solid fa-user" }
      ]
    };
  }
};

// ==========================================
// STRING & DATE UTILITIES
// ==========================================
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function formatDate(isoStr) {
  if (!isoStr) return '-';
  try {
    const d = new Date(isoStr);
    return d.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch {
    return isoStr;
  }
}

function formatDuration(seconds) {
  if (!seconds || seconds <= 0) return '0s';
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  if (mins === 0) return `${secs}s`;
  return `${mins}m ${secs}s`;
}

// DOM Ready
document.addEventListener('DOMContentLoaded', () => {
  ThemeManager.init();
  initNavbar();
  AIAssistantWidget.init();
});
