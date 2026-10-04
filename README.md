# ⚡ QuizNova – Online Quiz & Result System

> **"Challenge Your Mind. Track Your Growth."**

**QuizNova** is a modern, full-stack online assessment and result platform built with **Python FastAPI**, **SQLAlchemy**, **SQLite**, and vanilla **HTML5/CSS3/JavaScript**. It features real-time countdown timers, automated server-side score calculation, diagnostic question breakdowns, role-based authentication, and a dynamic podium leaderboard.

---

## 🌟 Key Features

### 🎓 Student Experience
- **Interactive Timed Quizzes:** Live countdown timer with subtle animations and low-time visual warnings.
- **Auto-Submission:** Automatically submits test answers when the timer reaches zero to prevent loss of progress.
- **Question Navigator Palette:** Interactive question grid tracking answered, unanswered, and current questions with jump-to-question capability.
- **Instant Result Evaluation:** Server-side score validation calculating percentage, correct answers, wrong answers, and unanswered questions.
- **Diagnostic Review:** Detailed post-test analysis showing questions, student choices, correct answers, and conceptual rationales.
- **Global & Per-Quiz Leaderboard:** Dynamic rankings with animated Top 3 podium cards (Gold, Silver, Bronze) and tabular listings.
- **Student Dashboard & Analytics:** Metrics tracking total quizzes completed, average score, and personal best score, paired with a search and filter system by category and difficulty.

### 🛡️ Administrator Panel
- **Institutional Analytics:** Real-time KPI cards displaying Total Students, Total Quizzes, Total Attempts, and Platform Average Score.
- **Dynamic Quiz Builder:** Interactive question authoring tool allowing admins to specify question text, 4 choices, select the correct answer via radio buttons, and attach explanations.
- **Catalog Management:** Toggle quizzes between **Draft** (hidden from students) and **Published** (live in student catalog) with one click, or delete obsolete quizzes.
- **Submission Monitoring:** Filter and search all student submissions across the institution with instant review access.

### 🔐 Security & Architecture
- **bcrypt Password Hashing:** Passwords are never stored as plain text.
- **JWT (JSON Web Token) Authorization:** Secure stateless authentication with automatic session expiration handling.
- **Role-Based Access Control (RBAC):** Backend-enforced authorization ensuring students cannot access administrative endpoints.
- **Input Validation & ORM Security:** Protection against SQL injection via SQLAlchemy parameterized queries and Pydantic schema validation.

---

## 🛠️ Technology Stack

| Layer | Technology | Details |
| :--- | :--- | :--- |
| **Frontend** | HTML5, CSS3, Vanilla JavaScript | Dark futuristic theme, glassmorphism, responsive grid & flexbox |
| **Icons & Fonts** | Font Awesome 6.5, Google Fonts | Outfit, Plus Jakarta Sans |
| **Backend** | Python 3, FastAPI, Starlette | High-performance asynchronous REST API |
| **Server** | Uvicorn | ASGI web server |
| **Database** | SQLite + SQLAlchemy 2.0 ORM | Auto-initializing database schema with automatic seed data |
| **Authentication**| Python-Jose, bcrypt | JWT Bearer tokens, secure password hashing |

---

## 📁 Project Structure

```
QuizNova/
├── main.py                  # FastAPI server, SQLAlchemy models, auth, REST endpoints
├── requirements.txt         # Core Python dependencies
├── README.md                # Comprehensive documentation
├── .gitignore               # Ignored files (pycache, env, logs)
│
├── database/
│   └── quiznova.db          # Auto-generated SQLite relational database
│
├── static/                  # Responsive frontend web pages and assets
│   ├── index.html           # Landing page with hero, statistics, features, and footer
│   ├── login.html           # Sign in page with 1-click demo buttons
│   ├── register.html        # Student registration page
│   ├── dashboard.html       # Student dashboard with stats cards, quiz grid, and filters
│   ├── quiz.html            # Timed assessment screen with question navigator
│   ├── result.html          # Performance score circle and diagnostic question review
│   ├── leaderboard.html     # Podium rankings and quiz filter
│   ├── profile.html         # User account details and historical attempts
│   ├── admin.html           # Admin dashboard with institutional statistics
│   ├── create-quiz.html     # Admin dynamic quiz builder form
│   ├── manage-quizzes.html  # Admin quiz catalog management (Draft/Publish toggles)
│   ├── results.html         # Admin student submissions analytics table
│   │
│   ├── css/
│   │   └── style.css        # Master stylesheet (dark futuristic glassmorphism)
│   │
│   └── js/
│       ├── app.js           # Auth state, API fetch client, toast system, modals
│       ├── auth.js          # Login & registration forms, demo fillers
│       ├── dashboard.js     # Student dashboard logic and filtering
│       ├── quiz.js          # Countdown timer, question palette, and submit flow
│       └── admin.js         # Admin dashboard, dynamic builder, and management
│
└── test_quiznova.py         # Automated end-to-end integration and security test suite
```

---

## 🚀 Quick Start Guide (Windows PowerShell)

### 1. Prerequisites
Ensure **Python 3.10+** is installed on your system.

Verify your installation:
```powershell
python --version
```

### 2. Navigate to Project Directory
```powershell
cd c:\Users\raahu\OneDrive\Documents\QuizNova
```

### 3. Install Required Dependencies
```powershell
python -m pip install -r requirements.txt
```

### 4. Configure Local Secrets
Copy `.env.example` to `.env` and set a private JWT signing key and demo account passwords. Keep `.env` local; it is excluded from Git.

### 5. Run the Application
Launch the server with Uvicorn:
```powershell
python -m uvicorn main:app --reload
```

The application will start immediately at:
👉 **http://127.0.0.1:8000**

*(The database and demo accounts are automatically initialized and seeded upon launch!)*

---

## 🔑 Demo Accounts

Use the **Student Login** and **Admin Login** buttons on the sign-in page to access the locally configured demo accounts. Their passwords are stored in `.env` and are never sent to the browser.

---

## 📋 Recommended Demo Walkthrough (30–60 Seconds)

1. **Landing Page:** Open `http://127.0.0.1:8000` to show the dark futuristic hero section, interactive metrics, and feature highlights.
2. **Student Login:** Click **Sign In**, click the **Student Login** demo button to auto-fill, and submit.
3. **Student Dashboard:** View the KPI stats cards (Available Quizzes, Completed, Avg Score, Best Score), search quizzes, or filter by category (`Web Dev`, `Database`, `Programming`).
4. **Take a Quiz:** Click **Start Quiz** on **Python Fundamentals**. Notice the countdown timer ticking, question palette updating as you answer, and progress bar filling.
5. **Submit Assessment:** Click **Submit Quiz** and confirm.
6. **Animated Results:** Observe the animated circular score gauge, percentage, custom performance feedback badge, and complete question diagnostic review.
7. **Leaderboard:** Click **View Leaderboard** to see the Gold, Silver, and Bronze podium cards.
8. **Admin Switch:** Sign out and use the **Admin Login** demo button.
9. **Admin Panel:** View platform stats, author a new quiz via the dynamic question builder, toggle published/draft status in the catalog, and inspect student submission logs.

---

## 🔌 API Overview

### Public & Authentication
- `POST /api/auth/register` – Register a new student or admin account.
- `POST /api/auth/login` – Authenticate credentials and receive a JWT Bearer token.
- `GET /api/auth/me` – Fetch current user profile and personal statistics.

### Student & Quizzes
- `GET /api/quizzes` – Retrieve all published quizzes with optional category/difficulty filters.
- `GET /api/quizzes/{id}` – Retrieve quiz details and questions (answer keys securely stripped).
- `POST /api/quizzes/{id}/submit` – Submit answers; backend evaluates and records score.
- `GET /api/attempts/{id}` – Retrieve detailed attempt report with question reviews and explanations.
- `GET /api/my-attempts` – Retrieve history of attempts for logged-in user.
- `GET /api/leaderboard` – Retrieve platform rankings sorted by percentage and completion time.

### Admin Protected
- `GET /api/admin/stats` – Platform-wide KPIs and recent activity log.
- `GET /api/admin/quizzes` – Complete quiz catalog including draft quizzes.
- `POST /api/admin/quizzes` – Author and publish a new quiz with multiple questions.
- `PATCH /api/admin/quizzes/{id}/toggle-publish` – Toggle quiz between Draft and Published.
- `DELETE /api/admin/quizzes/{id}` – Delete a quiz and associated records.
- `GET /api/admin/results` – All student submission records with search and filter.

---

## 🧪 Testing & Verification

A dedicated verification suite `test_quiznova.py` is included to validate the entire platform:
```powershell
python test_quiznova.py
```

**Verification Results:**
- ✅ 12/12 integration and security tests passing with 100% success.
- ✅ Role-based authorization enforced (403 Forbidden for non-admins).
- ✅ Relational SQLite database auto-initialization and seeding verified.
- ✅ Correct answer hiding on student quiz endpoints verified.

---

## 🔮 Future Enhancements
- Exportable PDF result certificates with digital verification QR codes.
- Multiplayer live quiz mode with WebSockets for classroom competition.
- Automated AI quiz generation from uploaded PDF textbooks or notes.
