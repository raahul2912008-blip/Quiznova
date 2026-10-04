/**
 * QUIZNOVA – QUIZ SYSTEM JAVASCRIPT
 * Handles Countdown Timer, Question Navigation, State Persistence, and Submission
 */

let quizData = null;
let currentQuestionIndex = 0;
let userAnswers = {}; // { questionId: 'A' }
let totalSeconds = 0;
let remainingSeconds = 0;
let timerInterval = null;
let isSubmitting = false;

document.addEventListener('DOMContentLoaded', () => {
  if (!Auth.requireAuth()) return;

  const urlParams = new URLSearchParams(window.location.search);
  const quizId = urlParams.get('id');

  if (!quizId) {
    showToast('Invalid Quiz', 'No quiz was specified.', 'error');
    setTimeout(() => window.location.href = '/dashboard.html', 1000);
    return;
  }

  loadQuiz(quizId);
});

async function loadQuiz(quizId) {
  const container = document.getElementById('quiz-app-container');
  if (!container) return;

  try {
    quizData = await apiFetch(`/api/quizzes/${quizId}`);

    if (!quizData.questions || quizData.questions.length === 0) {
      showToast('Empty Quiz', 'This quiz has no questions available.', 'error');
      setTimeout(() => window.location.href = '/dashboard.html', 1500);
      return;
    }

    // Set Header Info
    const titleEl = document.getElementById('quiz-header-title');
    if (titleEl) titleEl.textContent = quizData.title;

    // Set Timer
    totalSeconds = (quizData.duration || 10) * 60;
    remainingSeconds = totalSeconds;
    startTimer();

    // Render Question Palette
    renderQuestionPalette();

    // Render First Question
    displayQuestion(0);

    // Setup action buttons
    const prevBtn = document.getElementById('btn-prev');
    const nextBtn = document.getElementById('btn-next');
    const submitBtn = document.getElementById('btn-submit-quiz');

    if (prevBtn) {
      prevBtn.onclick = () => {
        if (currentQuestionIndex > 0) {
          displayQuestion(currentQuestionIndex - 1);
        }
      };
    }

    if (nextBtn) {
      nextBtn.onclick = () => {
        if (currentQuestionIndex < quizData.questions.length - 1) {
          displayQuestion(currentQuestionIndex + 1);
        } else {
          promptSubmit();
        }
      };
    }

    if (submitBtn) {
      submitBtn.onclick = promptSubmit;
    }

    // Warn on accidental tab close / reload
    window.addEventListener('beforeunload', handleBeforeUnload);

  } catch (err) {
    container.innerHTML = `
      <div class="empty-state">
        <i class="fa-solid fa-triangle-exclamation empty-state-icon" style="color: #ef4444;"></i>
        <h3>Unable to Launch Quiz</h3>
        <p>${escapeHtml(err.message)}</p>
        <a href="/dashboard.html" class="btn btn-secondary">Return to Dashboard</a>
      </div>
    `;
  }
}

function handleBeforeUnload(e) {
  if (!isSubmitting && remainingSeconds > 0) {
    e.preventDefault();
    e.returnValue = 'Your quiz progress will be lost if you leave now!';
    return e.returnValue;
  }
}

function startTimer() {
  const timerEl = document.getElementById('timer-display');
  const timerBox = document.getElementById('timer-box');

  const updateDisplay = () => {
    const mins = Math.floor(remainingSeconds / 60);
    const secs = remainingSeconds % 60;
    if (timerEl) {
      timerEl.textContent = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    }

    // Danger zone warning (< 60 seconds)
    if (remainingSeconds <= 60 && timerBox) {
      timerBox.classList.add('timer-warning');
    }

    if (remainingSeconds <= 0) {
      clearInterval(timerInterval);
      showToast('Time Expired', 'Submitting quiz automatically...', 'warning');
      submitQuiz(true);
    }

    remainingSeconds--;
  };

  updateDisplay();
  timerInterval = setInterval(updateDisplay, 1000);
}

function renderQuestionPalette() {
  const palette = document.getElementById('question-palette');
  if (!palette || !quizData) return;

  palette.innerHTML = quizData.questions.map((q, idx) => {
    const isAnswered = !!userAnswers[q.id];
    const isCurrent = idx === currentQuestionIndex;

    let classes = 'palette-btn';
    if (isAnswered) classes += ' answered';
    if (isCurrent) classes += ' current';

    return `
      <button class="${classes}" id="palette-btn-${idx}" onclick="displayQuestion(${idx})">
        ${idx + 1}
      </button>
    `;
  }).join('');
}

function displayQuestion(index) {
  if (!quizData || index < 0 || index >= quizData.questions.length) return;

  currentQuestionIndex = index;
  const q = quizData.questions[index];
  const total = quizData.questions.length;

  // Update counters
  const qNumTag = document.getElementById('question-number-tag');
  if (qNumTag) qNumTag.textContent = `Question ${index + 1} of ${total}`;

  // Update Progress Bar
  const progressFill = document.getElementById('quiz-progress-fill');
  if (progressFill) {
    const pct = ((index + 1) / total) * 100;
    progressFill.style.width = `${pct}%`;
  }

  // Update Question Text
  const qText = document.getElementById('question-text');
  if (qText) qText.textContent = q.question_text;

  // Render 4 Options
  const optionsWrapper = document.getElementById('options-container');
  if (optionsWrapper) {
    const selectedLetter = userAnswers[q.id] || null;

    const options = [
      { key: 'A', text: q.option_a },
      { key: 'B', text: q.option_b },
      { key: 'C', text: q.option_c },
      { key: 'D', text: q.option_d }
    ];

    optionsWrapper.innerHTML = options.map(opt => {
      const isSelected = selectedLetter === opt.key;
      return `
        <div class="option-box ${isSelected ? 'selected' : ''}" onclick="selectAnswer(${q.id}, '${opt.key}')">
          <div class="option-indicator">${opt.key}</div>
          <div class="option-text">${escapeHtml(opt.text)}</div>
        </div>
      `;
    }).join('');
  }

  // Update Previous / Next Buttons
  const prevBtn = document.getElementById('btn-prev');
  const nextBtn = document.getElementById('btn-next');

  if (prevBtn) {
    prevBtn.disabled = index === 0;
    prevBtn.style.opacity = index === 0 ? '0.4' : '1';
  }

  if (nextBtn) {
    if (index === total - 1) {
      nextBtn.innerHTML = `Review & Submit <i class="fa-solid fa-flag-checkered"></i>`;
    } else {
      nextBtn.innerHTML = `Next <i class="fa-solid fa-arrow-right"></i>`;
    }
  }

  // Highlight in Palette
  renderQuestionPalette();
}

function selectAnswer(questionId, letter) {
  userAnswers[questionId] = letter;

  // Re-render options to update active class
  displayQuestion(currentQuestionIndex);
}

function promptSubmit() {
  if (isSubmitting) return;

  const total = quizData.questions.length;
  const answeredCount = Object.keys(userAnswers).length;
  const unansweredCount = total - answeredCount;

  let msg = `You have answered ${answeredCount} of ${total} questions.`;
  if (unansweredCount > 0) {
    msg += ` Warning: ${unansweredCount} question(s) are still unanswered. Are you sure you want to finish?`;
  } else {
    msg += ` Great job! Ready to calculate your final score?`;
  }

  showConfirmModal({
    title: 'Submit Quiz',
    message: msg,
    confirmText: 'Yes, Submit Now',
    cancelText: 'Keep Answering',
    confirmClass: 'btn-primary',
    onConfirm: () => submitQuiz(false)
  });
}

async function submitQuiz(forced = false) {
  if (isSubmitting) return;
  isSubmitting = true;

  if (timerInterval) clearInterval(timerInterval);
  window.removeEventListener('beforeunload', handleBeforeUnload);

  const submitBtn = document.getElementById('btn-submit-quiz');
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<span class="spinner"></span> Grading...`;
  }

  const timeTaken = totalSeconds - Math.max(0, remainingSeconds);

  try {
    const payload = {
      answers: userAnswers,
      time_taken: timeTaken
    };

    const result = await apiFetch(`/api/quizzes/${quizData.id}/submit`, {
      method: 'POST',
      body: payload
    });

    showToast('Quiz Evaluated!', `You scored ${result.percentage}% (${result.score}/${result.total_questions})`, 'success');

    setTimeout(() => {
      window.location.href = `/result.html?attempt_id=${result.attempt_id}`;
    }, 700);

  } catch (err) {
    isSubmitting = false;
    showToast('Submission Error', err.message || 'Failed to submit quiz.', 'error');
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = `Submit Quiz`;
    }
  }
}
