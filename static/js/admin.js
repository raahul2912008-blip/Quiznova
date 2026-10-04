/**
 * QUIZNOVA – ADMIN PANEL JAVASCRIPT
 * Handles Platform Stats, Quiz Creation with Dynamic Questions, Quiz Management, and Results Analytics
 */

document.addEventListener('DOMContentLoaded', () => {
  if (!Auth.requireAdmin()) return;

  const path = window.location.pathname;

  if (path.includes('admin.html') || path.endsWith('/admin')) {
    loadAdminStats();
  } else if (path.includes('create-quiz')) {
    initQuizBuilder();
  } else if (path.includes('manage-quizzes')) {
    loadManageQuizzes();
  } else if (path.includes('results')) {
    loadAdminResults();
  }
});

// ==========================================
// ADMIN DASHBOARD STATS
// ==========================================
async function loadAdminStats() {
  try {
    const data = await apiFetch('/api/admin/stats');

    const elStudents = document.getElementById('admin-stat-students');
    const elQuizzes = document.getElementById('admin-stat-quizzes');
    const elAttempts = document.getElementById('admin-stat-attempts');
    const elAvg = document.getElementById('admin-stat-avg');

    if (elStudents) elStudents.textContent = data.total_students;
    if (elQuizzes) elQuizzes.textContent = data.total_quizzes;
    if (elAttempts) elAttempts.textContent = data.total_attempts;
    if (elAvg) elAvg.textContent = `${data.average_score}%`;

    // Render recent attempts
    const tbody = document.getElementById('admin-recent-tbody');
    if (tbody) {
      if (!data.recent_attempts || data.recent_attempts.length === 0) {
        tbody.innerHTML = `
          <tr>
            <td colspan="5" style="text-align: center; padding: 2rem; color: var(--text-muted);">
              No student attempts recorded yet.
            </td>
          </tr>
        `;
        return;
      }

      tbody.innerHTML = data.recent_attempts.map(att => `
        <tr>
          <td style="font-weight: 600; color: #fff;">
            ${escapeHtml(att.student_name)}
            <div style="font-size: 0.78rem; color: var(--text-sub); font-weight: normal;">${escapeHtml(att.student_email)}</div>
          </td>
          <td style="color: #c4b5fd;">${escapeHtml(att.quiz_title)}</td>
          <td>
            <span class="badge ${att.percentage >= 70 ? 'badge-green' : 'badge-amber'}">
              ${att.percentage}% (${att.score}/${att.total_questions})
            </span>
          </td>
          <td style="color: var(--text-muted); font-size: 0.85rem;">${formatDate(att.completed_at)}</td>
          <td>
            <a href="/result.html?attempt_id=${att.id}" class="btn btn-secondary btn-sm" target="_blank">
              <i class="fa-solid fa-eye"></i> View
            </a>
          </td>
        </tr>
      `).join('');
    }
  } catch (err) {
    showToast('Admin Error', err.message, 'error');
  }
}

// ==========================================
// DYNAMIC QUIZ BUILDER
// ==========================================
let questionCount = 0;

function initQuizBuilder() {
  const addBtn = document.getElementById('btn-add-question');
  const form = document.getElementById('create-quiz-form');

  if (addBtn) {
    addBtn.addEventListener('click', () => addQuestionBlock());
  }

  // Add initial question
  addQuestionBlock();

  if (form) {
    form.addEventListener('submit', handleCreateQuizSubmit);
  }
}

function addQuestionBlock() {
  questionCount++;
  const container = document.getElementById('questions-builder-container');
  if (!container) return;

  const currentIdx = questionCount;
  const block = document.createElement('div');
  block.className = 'question-builder-item';
  block.id = `qb-item-${currentIdx}`;

  block.innerHTML = `
    <div class="qb-header">
      <span class="qb-title">Question #${currentIdx}</span>
      ${currentIdx > 1 ? `
        <button type="button" class="btn btn-outline-danger btn-sm" onclick="removeQuestionBlock(${currentIdx})">
          <i class="fa-solid fa-trash"></i> Remove
        </button>
      ` : ''}
    </div>

    <div class="form-group">
      <label class="form-label">Question Text *</label>
      <textarea class="form-input qb-question-text" rows="2" placeholder="e.g. What is the output of print(2 + 2)?" required></textarea>
    </div>

    <div style="font-size: 0.85rem; font-weight: 600; color: var(--text-muted); margin-bottom: 0.6rem;">
      Answer Options & Correct Answer Selection:
    </div>

    <div class="options-builder-grid">
      <div class="option-builder-field">
        <input type="radio" name="correct_answer_${currentIdx}" value="A" class="radio-correct-custom" checked title="Mark Option A as Correct">
        <input type="text" class="form-input qb-opt-a" placeholder="Option A text *" required>
      </div>

      <div class="option-builder-field">
        <input type="radio" name="correct_answer_${currentIdx}" value="B" class="radio-correct-custom" title="Mark Option B as Correct">
        <input type="text" class="form-input qb-opt-b" placeholder="Option B text *" required>
      </div>

      <div class="option-builder-field">
        <input type="radio" name="correct_answer_${currentIdx}" value="C" class="radio-correct-custom" title="Mark Option C as Correct">
        <input type="text" class="form-input qb-opt-c" placeholder="Option C text *" required>
      </div>

      <div class="option-builder-field">
        <input type="radio" name="correct_answer_${currentIdx}" value="D" class="radio-correct-custom" title="Mark Option D as Correct">
        <input type="text" class="form-input qb-opt-d" placeholder="Option D text *" required>
      </div>
    </div>

    <div class="form-group" style="margin-top: 1rem;">
      <label class="form-label">Explanation (Optional - shown after test submission)</label>
      <input type="text" class="form-input qb-explanation" placeholder="Brief rationale for the correct answer...">
    </div>
  `;

  container.appendChild(block);
  updateQuestionCounters();
}

function removeQuestionBlock(idx) {
  const block = document.getElementById(`qb-item-${idx}`);
  if (block) {
    block.remove();
    updateQuestionCounters();
  }
}

function updateQuestionCounters() {
  const blocks = document.querySelectorAll('.question-builder-item');
  const countDisplay = document.getElementById('total-questions-counter');
  if (countDisplay) {
    countDisplay.textContent = blocks.length;
  }
  blocks.forEach((el, i) => {
    const title = el.querySelector('.qb-title');
    if (title) title.textContent = `Question #${i + 1}`;
  });
}

async function handleCreateQuizSubmit(e) {
  e.preventDefault();

  const title = document.getElementById('quiz-title').value.trim();
  const description = document.getElementById('quiz-description').value.trim();
  const category = document.getElementById('quiz-category').value.trim();
  const difficulty = document.getElementById('quiz-difficulty').value;
  const duration = parseInt(document.getElementById('quiz-duration').value, 10);
  const isPublished = document.getElementById('quiz-publish-status').value === 'true';

  const questionBlocks = document.querySelectorAll('.question-builder-item');

  if (questionBlocks.length === 0) {
    showToast('Missing Questions', 'Please add at least one question.', 'warning');
    return;
  }

  const questionsPayload = [];

  for (let block of questionBlocks) {
    const qText = block.querySelector('.qb-question-text').value.trim();
    const optA = block.querySelector('.qb-opt-a').value.trim();
    const optB = block.querySelector('.qb-opt-b').value.trim();
    const optC = block.querySelector('.qb-opt-c').value.trim();
    const optD = block.querySelector('.qb-opt-d').value.trim();
    const expl = block.querySelector('.qb-explanation').value.trim();

    const selectedRadio = block.querySelector('input[type="radio"]:checked');
    const correct = selectedRadio ? selectedRadio.value : 'A';

    if (!qText || !optA || !optB || !optC || !optD) {
      showToast('Validation Error', 'Please complete all question fields and options.', 'warning');
      return;
    }

    questionsPayload.push({
      question_text: qText,
      option_a: optA,
      option_b: optB,
      option_c: optC,
      option_d: optD,
      correct_answer: correct,
      explanation: expl
    });
  }

  const submitBtn = document.getElementById('btn-submit-create-quiz');
  const originalHtml = submitBtn.innerHTML;

  try {
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<span class="spinner"></span> Creating Quiz...`;

    const payload = {
      title,
      description,
      category,
      difficulty,
      duration,
      is_published: isPublished,
      questions: questionsPayload
    };

    const res = await apiFetch('/api/admin/quizzes', {
      method: 'POST',
      body: payload
    });

    showToast('Quiz Created!', `"${res.title}" with ${res.question_count} questions has been saved!`, 'success');

    setTimeout(() => {
      window.location.href = '/manage-quizzes.html';
    }, 800);
  } catch (err) {
    showToast('Creation Failed', err.message, 'error');
    submitBtn.disabled = false;
    submitBtn.innerHTML = originalHtml;
  }
}

// ==========================================
// QUIZ MANAGEMENT TABLE
// ==========================================
let allAdminQuizzes = [];

async function loadManageQuizzes() {
  const tbody = document.getElementById('manage-quizzes-tbody');
  if (!tbody) return;

  try {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" style="text-align: center; padding: 2rem;">
          <span class="spinner"></span>
          <p style="color: var(--text-muted); margin-top: 8px;">Loading quizzes...</p>
        </td>
      </tr>
    `;

    allAdminQuizzes = await apiFetch('/api/admin/quizzes');
    renderAdminQuizzes(allAdminQuizzes);
    setupAdminSearch();
  } catch (err) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" style="text-align: center; padding: 2rem; color: #ef4444;">
          Error: ${escapeHtml(err.message)}
        </td>
      </tr>
    `;
  }
}

function renderAdminQuizzes(quizzes) {
  const tbody = document.getElementById('manage-quizzes-tbody');
  if (!tbody) return;

  if (quizzes.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" style="text-align: center; padding: 2rem; color: var(--text-muted);">
          No quizzes found. Click "+ Create Quiz" to author your first assessment!
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = quizzes.map(q => {
    const statusBadge = q.is_published
      ? `<span class="badge badge-green"><i class="fa-solid fa-circle"></i> Published</span>`
      : `<span class="badge badge-gray"><i class="fa-solid fa-circle-dot"></i> Draft</span>`;

    return `
      <tr>
        <td style="font-weight: 700; color: #fff;">
          ${escapeHtml(q.title)}
          <div style="font-size: 0.78rem; color: var(--text-sub);">${escapeHtml(q.category)} &bull; ${q.difficulty}</div>
        </td>
        <td>${q.question_count} Qs</td>
        <td>${q.duration} Mins</td>
        <td>${q.attempt_count} Attempts</td>
        <td>${statusBadge}</td>
        <td style="color: var(--text-muted); font-size: 0.85rem;">${formatDate(q.created_at)}</td>
        <td>
          <div style="display: flex; gap: 6px;">
            <button class="btn btn-secondary btn-sm" onclick="togglePublishQuiz(${q.id})" title="Toggle Draft / Published">
              <i class="fa-solid fa-repeat"></i> ${q.is_published ? 'Unpublish' : 'Publish'}
            </button>
            <button class="btn btn-outline-danger btn-sm" onclick="confirmDeleteQuiz(${q.id}, '${escapeHtml(q.title).replace(/'/g, "\\'")}')" title="Delete Quiz">
              <i class="fa-solid fa-trash"></i>
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

function setupAdminSearch() {
  const search = document.getElementById('search-admin-quizzes');
  if (!search) return;

  search.addEventListener('input', () => {
    const val = search.value.toLowerCase().trim();
    const filtered = allAdminQuizzes.filter(q =>
      q.title.toLowerCase().includes(val) ||
      q.category.toLowerCase().includes(val)
    );
    renderAdminQuizzes(filtered);
  });
}

async function togglePublishQuiz(id) {
  try {
    const res = await apiFetch(`/api/admin/quizzes/${id}/toggle-publish`, {
      method: 'PATCH'
    });
    showToast('Status Updated', res.message, 'success');
    loadManageQuizzes();
  } catch (err) {
    showToast('Update Error', err.message, 'error');
  }
}

function confirmDeleteQuiz(id, title) {
  showConfirmModal({
    title: 'Delete Quiz',
    message: `Are you sure you want to permanently delete "${title}"? All associated questions and student attempts will also be removed.`,
    confirmText: 'Delete Quiz',
    cancelText: 'Cancel',
    confirmClass: 'btn-danger',
    onConfirm: async () => {
      try {
        const res = await apiFetch(`/api/admin/quizzes/${id}`, {
          method: 'DELETE'
        });
        showToast('Quiz Deleted', res.message, 'info');
        loadManageQuizzes();
      } catch (err) {
        showToast('Delete Error', err.message, 'error');
      }
    }
  });
}

// ==========================================
// ADMIN RESULTS MANAGEMENT
// ==========================================
let allAdminResults = [];

async function loadAdminResults() {
  const tbody = document.getElementById('admin-results-tbody');
  const quizFilter = document.getElementById('results-quiz-filter');
  const searchInput = document.getElementById('results-search');

  if (!tbody) return;

  try {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" style="text-align: center; padding: 2rem;">
          <span class="spinner"></span>
          <p style="color: var(--text-muted); margin-top: 8px;">Loading all results...</p>
        </td>
      </tr>
    `;

    const data = await apiFetch('/api/admin/results');
    allAdminResults = data.results || [];

    // Populate quiz filter dropdown
    if (quizFilter && data.quizzes) {
      quizFilter.innerHTML = `<option value="">All Quizzes</option>` +
        data.quizzes.map(q => `<option value="${q.id}">${escapeHtml(q.title)}</option>`).join('');

      quizFilter.onchange = applyResultsFilter;
    }

    if (searchInput) {
      searchInput.oninput = applyResultsFilter;
    }

    renderAdminResults(allAdminResults);
  } catch (err) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" style="text-align: center; padding: 2rem; color: #ef4444;">
          Error: ${escapeHtml(err.message)}
        </td>
      </tr>
    `;
  }
}

function applyResultsFilter() {
  const quizFilter = document.getElementById('results-quiz-filter');
  const searchInput = document.getElementById('results-search');

  const selectedQuizId = quizFilter ? quizFilter.value : '';
  const searchVal = searchInput ? searchInput.value.toLowerCase().trim() : '';

  const filtered = allAdminResults.filter(r => {
    const matchQuiz = !selectedQuizId || String(r.quiz_id) === String(selectedQuizId);
    const matchSearch = !searchVal ||
      r.student_name.toLowerCase().includes(searchVal) ||
      r.student_email.toLowerCase().includes(searchVal) ||
      r.quiz_title.toLowerCase().includes(searchVal);

    return matchQuiz && matchSearch;
  });

  renderAdminResults(filtered);
}

function renderAdminResults(results) {
  const tbody = document.getElementById('admin-results-tbody');
  if (!tbody) return;

  if (results.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" style="text-align: center; padding: 2rem; color: var(--text-muted);">
          No matching quiz results found.
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = results.map(r => {
    const pct = r.percentage;
    let badgeClass = 'badge-red';
    if (pct >= 85) badgeClass = 'badge-green';
    else if (pct >= 60) badgeClass = 'badge-amber';

    return `
      <tr>
        <td style="font-weight: 600; color: #fff;">
          ${escapeHtml(r.student_name)}
        </td>
        <td style="color: var(--text-muted); font-size: 0.88rem;">${escapeHtml(r.student_email)}</td>
        <td style="color: #c4b5fd;">${escapeHtml(r.quiz_title)}</td>
        <td>
          <span class="badge ${badgeClass}">${pct}% (${r.score}/${r.total_questions})</span>
        </td>
        <td style="color: var(--text-muted); font-size: 0.85rem;">${formatDuration(r.time_taken)}</td>
        <td style="color: var(--text-muted); font-size: 0.85rem;">${formatDate(r.completed_at)}</td>
        <td>
          <a href="/result.html?attempt_id=${r.id}" class="btn btn-secondary btn-sm" target="_blank">
            <i class="fa-solid fa-file-lines"></i> Review
          </a>
        </td>
      </tr>
    `;
  }).join('');
}
