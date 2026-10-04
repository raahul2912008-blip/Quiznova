/**
 * QUIZNOVA – EDUCATIONAL DASHBOARD JAVASCRIPT
 * Handles Student Learning Progress, Real Weekly Activity Visualization,
 * "Continue Learning" banner, Course-Style Quiz Cards, and Real Data Integration.
 */

let allQuizzes = [];

document.addEventListener('DOMContentLoaded', () => {
  if (!Auth.requireAuth()) return;

  loadStudentDashboard();
  setupFilterListeners();
});

async function loadStudentDashboard() {
  await Promise.all([
    loadLearningProgress(),
    loadQuizzes(),
    loadRecentAttempts()
  ]);
}

/**
 * Loads real learning metrics, weekly streak, activity bars,
 * weekly goal progress, and recent quiz card.
 */
async function loadLearningProgress() {
  try {
    const data = await apiFetch('/api/student/learning-progress');

    // 1. Dynamic Student Name
    const welcomeEl = document.getElementById('welcome-username');
    if (welcomeEl) {
      welcomeEl.textContent = data.first_name || data.user_name || 'Learner';
    }

    // 2. Learning Streak & Banner
    const streakBannerText = document.getElementById('streak-banner-text');
    const statStreak = document.getElementById('stat-streak');
    const streakDays = data.streak_days || 0;

    if (statStreak) statStreak.textContent = streakDays;
    if (streakBannerText) {
      if (streakDays > 0) {
        streakBannerText.textContent = `${streakDays}-Day Learning Streak · You're making great progress. Keep your learning streak going!`;
      } else {
        streakBannerText.textContent = `You're making great progress. Keep your learning streak going!`;
      }
    }

    // 3. Stat Metrics
    const elCompleted = document.getElementById('stat-completed');
    const elAvg = document.getElementById('stat-avg-score');
    const elBest = document.getElementById('stat-best-score');

    if (elCompleted) elCompleted.textContent = data.quizzes_completed || 0;
    if (elAvg) elAvg.textContent = `${data.average_score || 0}%`;
    if (elBest) elBest.textContent = `${data.best_score || 0}%`;

    // 4. Sidebar Weekly Goal
    const goal = data.weekly_goal || { target: 3, completed: 0, percentage: 0 };
    const goalFill = document.getElementById('goal-progress-fill');
    const goalCount = document.getElementById('goal-progress-count');
    const goalPct = document.getElementById('goal-progress-pct');

    if (goalFill) goalFill.style.width = `${goal.percentage}%`;
    if (goalCount) goalCount.textContent = `${goal.completed} of ${goal.target} completed`;
    if (goalPct) goalPct.textContent = `${goal.percentage}%`;

    // 5. Weekly Activity Visualization (Mon - Sun real bars)
    renderWeeklyActivity(data.weekly_activity || []);

    // 6. Continue Learning Card
    renderContinueLearning(data.continue_learning);

  } catch (err) {
    console.error('Failed to load learning progress:', err);
  }
}

/**
 * Renders weekly activity column bars for past 7 days based on real attempts.
 */
function renderWeeklyActivity(days) {
  const container = document.getElementById('weekly-bars-container');
  if (!container) return;

  if (!days || days.length === 0) {
    container.innerHTML = `<span style="font-size: 0.8rem; color: var(--text-sub);">No activity logged this week</span>`;
    return;
  }

  // Find max count for scaling (minimum 1 to avoid / 0)
  const maxCount = Math.max(...days.map(d => d.count), 1);

  container.innerHTML = days.map(d => {
    const heightPct = d.count > 0 ? Math.max(25, Math.round((d.count / maxCount) * 100)) : 10;
    const activeClass = d.count > 0 ? 'active' : '';
    const todayClass = d.is_today ? 'today' : '';
    const tooltipText = `${d.day}: ${d.count} quiz${d.count === 1 ? '' : 'zes'}`;

    return `
      <div class="activity-col" title="${tooltipText}">
        <div class="activity-bar-fill ${activeClass} ${todayClass}" style="height: ${heightPct}%;"></div>
        <span class="activity-col-label" style="${d.is_today ? 'color: var(--accent-amber); font-weight: 700;' : ''}">${d.day}</span>
      </div>
    `;
  }).join('');
}

/**
 * Renders the top "Continue Learning" banner.
 */
function renderContinueLearning(recentQuiz) {
  const container = document.getElementById('continue-learning-container');
  if (!container) return;

  if (recentQuiz) {
    const categoryIcon = getCategoryIcon(recentQuiz.quiz_category);
    const difficultyLabel = getDifficultyLabel(recentQuiz.quiz_difficulty);

    container.innerHTML = `
      <div class="continue-card">
        <div class="continue-card-info">
          <div style="font-size: 0.78rem; text-transform: uppercase; font-weight: 700; color: var(--accent-primary); letter-spacing: 0.05em; margin-bottom: 4px;">
            <i class="fa-solid fa-clock-rotate-left"></i> Your latest practice
          </div>
          <h3>${escapeHtml(recentQuiz.quiz_title)}</h3>
          <div class="continue-meta">
            <span><i class="${categoryIcon}"></i> ${escapeHtml(recentQuiz.quiz_category)}</span>
            <span>&bull;</span>
            <span>${difficultyLabel}</span>
            <span>&bull;</span>
            <span class="badge ${recentQuiz.percentage >= 70 ? 'badge-green' : 'badge-amber'}">
              Last score: ${recentQuiz.percentage}% (${recentQuiz.score}/${recentQuiz.total_questions})
            </span>
            <span>&bull;</span>
            <span style="color: var(--text-sub);"><i class="fa-solid fa-calendar-check"></i> ${formatDate(recentQuiz.completed_at)}</span>
          </div>
        </div>
        <div>
          <a href="/quiz.html?id=${recentQuiz.quiz_id}" class="btn btn-primary">
            <i class="fa-solid fa-rotate-right"></i> Retake Quiz
          </a>
        </div>
      </div>
    `;
  } else {
    container.innerHTML = `
      <div class="continue-card continue-card-empty">
        <div class="continue-card-info">
          <div style="font-size: 0.78rem; text-transform: uppercase; font-weight: 700; color: var(--accent-amber); letter-spacing: 0.05em; margin-bottom: 4px;">
            <i class="fa-solid fa-compass"></i> A fresh start
          </div>
          <h3>Ready for your next learning win?</h3>
          <div class="continue-meta">
            <span>Choose any published quiz below and make today a little more curious.</span>
          </div>
        </div>
        <div>
          <a href="#available-quizzes-section" class="btn btn-primary">
            <i class="fa-solid fa-book-open"></i> Explore quizzes
          </a>
        </div>
      </div>
    `;
  }
}

/**
 * Loads and renders course-style quiz cards.
 */
async function loadQuizzes() {
  const container = document.getElementById('quizzes-container');
  if (!container) return;

  try {
    container.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 3rem;">
        <span class="spinner"></span>
        <p style="color: var(--text-muted); margin-top: 10px;">Loading educational topics...</p>
      </div>
    `;

    allQuizzes = await apiFetch('/api/quizzes');
    renderQuizzes(allQuizzes);
  } catch (err) {
    container.innerHTML = `
      <div class="empty-state" style="grid-column: 1 / -1;">
        <i class="fa-solid fa-triangle-exclamation empty-state-icon" style="color: var(--accent-rose);"></i>
        <h3>Unable to Load Topics</h3>
        <p>${escapeHtml(err.message)}</p>
        <button class="btn btn-secondary" onclick="loadQuizzes()">Retry</button>
      </div>
    `;
  }
}

function renderQuizzes(quizzes) {
  const container = document.getElementById('quizzes-container');
  if (!container) return;

  if (quizzes.length === 0) {
    container.innerHTML = `
      <div class="empty-state" style="grid-column: 1 / -1;">
        <i class="fa-solid fa-magnifying-glass empty-state-icon"></i>
        <h3>No Quizzes Match Your Search</h3>
        <p>Try searching for a different keyword or category.</p>
        <button class="btn btn-secondary btn-sm" onclick="resetFilters()">Clear Filters</button>
      </div>
    `;
    return;
  }

  container.innerHTML = quizzes.map(q => {
    const categoryIcon = getCategoryIcon(q.category);
    const categoryBadgeClass = getCategoryBadgeClass(q.category);
    const difficultyLabel = getDifficultyLabel(q.difficulty);
    const difficultyBadgeClass = getDifficultyBadgeClass(q.difficulty);

    const completedBadge = q.completed
      ? `<span class="badge badge-blue"><i class="fa-solid fa-rotate-right"></i> Previously attempted</span>`
      : `<span style="font-size: 0.78rem; color: var(--text-sub);"><i class="fa-solid fa-book-open"></i> Ready to practice</span>`;
    const scoreProgress = q.completed && q.best_percentage !== null
      ? `<div class="quiz-score-progress" aria-label="Best score ${q.best_percentage}%">
          <div class="quiz-score-progress-label"><span>Personal best</span><strong>${q.best_percentage}%</strong></div>
          <div class="quiz-score-progress-track"><span style="width: ${Math.min(100, Math.max(0, q.best_percentage))}%"></span></div>
        </div>`
      : '';

    return `
      <div class="quiz-card" data-category="${escapeHtml(q.category)}">
        <div class="quiz-card-top-accent"></div>
        <div class="quiz-card-body">
          <div class="quiz-card-header">
            <span class="badge ${categoryBadgeClass}">
              <i class="${categoryIcon}"></i> ${escapeHtml(q.category)}
            </span>
            <span class="badge ${difficultyBadgeClass}">
              ${difficultyLabel}
            </span>
          </div>

          <h3 class="quiz-card-title">${escapeHtml(q.title)}</h3>
          <p class="quiz-card-desc">${escapeHtml(q.description || 'Test your knowledge and prove your skills in this interactive practice quiz.')}</p>

          <div class="quiz-meta-row">
            <div class="meta-item">
              <i class="fa-solid fa-circle-question" style="color: var(--accent-primary);"></i>
              <span>${q.question_count} Questions</span>
            </div>
            <div class="meta-item">
              <i class="fa-solid fa-clock" style="color: var(--accent-teal);"></i>
              <span>${q.duration} min</span>
            </div>
          </div>
          ${scoreProgress}
        </div>

        <div class="quiz-card-footer">
          <div class="quiz-status-pill">
            ${completedBadge}
          </div>
          <a href="/quiz.html?id=${q.id}" class="btn ${q.completed ? 'btn-secondary' : 'btn-primary'} btn-sm">
            <i class="fa-solid ${q.completed ? 'fa-rotate-right' : 'fa-play'}"></i>
            ${q.completed ? 'Retake Quiz' : 'Start Quiz'}
          </a>
        </div>
      </div>
    `;
  }).join('');
}

function getCategoryIcon(category) {
  const cat = (category || '').toLowerCase();
  if (cat.includes('program') || cat.includes('code') || cat.includes('python') || cat.includes('java')) {
    return 'fa-solid fa-code';
  }
  if (cat.includes('data') || cat.includes('sql')) {
    return 'fa-solid fa-database';
  }
  if (cat.includes('web') || cat.includes('frontend') || cat.includes('html')) {
    return 'fa-solid fa-laptop-code';
  }
  if (cat.includes('devops') || cat.includes('cloud') || cat.includes('server')) {
    return 'fa-solid fa-server';
  }
  if (cat.includes('math')) {
    return 'fa-solid fa-calculator';
  }
  if (cat.includes('science')) {
    return 'fa-solid fa-flask';
  }
  return 'fa-solid fa-book-open';
}

function getCategoryBadgeClass(category) {
  const cat = (category || '').toLowerCase();
  if (cat.includes('program') || cat.includes('code') || cat.includes('python') || cat.includes('java')) {
    return 'badge-blue';
  }
  if (cat.includes('data') || cat.includes('sql')) {
    return 'badge-teal';
  }
  if (cat.includes('web') || cat.includes('frontend') || cat.includes('html')) {
    return 'badge-indigo';
  }
  if (cat.includes('devops') || cat.includes('cloud') || cat.includes('server')) {
    return 'badge-purple';
  }
  if (cat.includes('math')) {
    return 'badge-amber';
  }
  if (cat.includes('science')) {
    return 'badge-green';
  }
  return 'badge-cyan';
}

function getDifficultyLabel(diff) {
  const d = (diff || '').toLowerCase();
  if (d === 'easy') return 'Beginner';
  if (d === 'medium') return 'Intermediate';
  if (d === 'hard') return 'Advanced';
  return diff || 'General';
}

function getDifficultyBadgeClass(diff) {
  const d = (diff || '').toLowerCase();
  if (d === 'easy') return 'badge-teal';
  if (d === 'medium') return 'badge-blue';
  if (d === 'hard') return 'badge-purple';
  return 'badge-gray';
}

function setupFilterListeners() {
  const searchInput = document.getElementById('search-quiz-input');
  const categorySelect = document.getElementById('filter-category');
  const difficultySelect = document.getElementById('filter-difficulty');

  const applyFilters = () => {
    const searchVal = searchInput ? searchInput.value.toLowerCase().trim() : '';
    const categoryVal = categorySelect ? categorySelect.value : 'all';
    const diffVal = difficultySelect ? difficultySelect.value : 'all';

    const filtered = allQuizzes.filter(q => {
      const matchSearch = !searchVal ||
        q.title.toLowerCase().includes(searchVal) ||
        q.category.toLowerCase().includes(searchVal) ||
        (q.description && q.description.toLowerCase().includes(searchVal));

      const matchCategory = categoryVal === 'all' || q.category.toLowerCase().includes(categoryVal.toLowerCase());
      const matchDiff = diffVal === 'all' || q.difficulty.toLowerCase() === diffVal.toLowerCase();

      return matchSearch && matchCategory && matchDiff;
    });

    renderQuizzes(filtered);
  };

  if (searchInput) searchInput.addEventListener('input', applyFilters);
  if (categorySelect) categorySelect.addEventListener('change', applyFilters);
  if (difficultySelect) difficultySelect.addEventListener('change', applyFilters);
}

function resetFilters() {
  const searchInput = document.getElementById('search-quiz-input');
  const categorySelect = document.getElementById('filter-category');
  const difficultySelect = document.getElementById('filter-difficulty');

  if (searchInput) searchInput.value = '';
  if (categorySelect) categorySelect.value = 'all';
  if (difficultySelect) difficultySelect.value = 'all';

  renderQuizzes(allQuizzes);
}

async function loadRecentAttempts() {
  const tableBody = document.getElementById('recent-attempts-tbody');
  if (!tableBody) return;

  try {
    const attempts = await apiFetch('/api/my-attempts');

    if (!attempts || attempts.length === 0) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="5" style="text-align: center; padding: 2.2rem; color: var(--text-muted);">
            No practice sessions recorded yet. Pick a quiz above to start your journey!
          </td>
        </tr>
      `;
      return;
    }

    tableBody.innerHTML = attempts.slice(0, 5).map(att => {
      const pct = att.percentage;
      let badge = 'badge-red';
      if (pct >= 85) badge = 'badge-green';
      else if (pct >= 60) badge = 'badge-amber';

      return `
        <tr>
          <td style="font-weight: 600; color: var(--text-main);">
            <i class="${getCategoryIcon(att.quiz_category)}" style="color: var(--accent-primary); margin-right: 6px;"></i>
            ${escapeHtml(att.quiz_title)}
          </td>
          <td>
            <span class="badge ${badge}">${pct}% (${att.score}/${att.total_questions})</span>
          </td>
          <td style="color: var(--text-muted); font-size: 0.85rem;">
            ${formatDuration(att.time_taken)}
          </td>
          <td style="color: var(--text-muted); font-size: 0.85rem;">
            ${formatDate(att.completed_at)}
          </td>
          <td>
            <a href="/result.html?attempt_id=${att.id}" class="btn btn-secondary btn-sm">
              <i class="fa-solid fa-file-lines"></i> Review Answers
            </a>
          </td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    console.error('Failed to load recent attempts:', err);
  }
}
