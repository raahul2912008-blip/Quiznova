import os
import datetime
import secrets
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, status, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, Float, DateTime, ForeignKey, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship
import bcrypt
from jose import JWTError, jwt

# ==========================================
# CONSTANTS & CONFIGURATION
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))
DATABASE_DIR = os.path.join(BASE_DIR, "database")
os.makedirs(DATABASE_DIR, exist_ok=True)

DB_PATH = os.path.join(DATABASE_DIR, "quiznova.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

SECRET_KEY = os.getenv("QUIZNOVA_SECRET_KEY")
DEMO_ADMIN_PASSWORD = os.getenv("QUIZNOVA_DEMO_ADMIN_PASSWORD")
DEMO_STUDENT_PASSWORD = os.getenv("QUIZNOVA_DEMO_STUDENT_PASSWORD")
if not SECRET_KEY or not DEMO_ADMIN_PASSWORD or not DEMO_STUDENT_PASSWORD:
    raise RuntimeError(
        "Set QUIZNOVA_SECRET_KEY and both demo-account passwords in the environment or project .env file."
    )
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# ==========================================
# DATABASE SETUP
# ==========================================
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================================
# SQLALCHEMY MODELS
# ==========================================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="STUDENT", nullable=False)  # "STUDENT" or "ADMIN"
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    attempts = relationship("QuizAttempt", back_populates="user", cascade="all, delete-orphan")

class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), default="General", nullable=False)
    difficulty = Column(String(20), default="Medium", nullable=False)  # Easy, Medium, Hard
    duration = Column(Integer, default=10, nullable=False)  # Duration in minutes
    is_published = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    questions = relationship("Question", back_populates="quiz", cascade="all, delete-orphan")
    attempts = relationship("QuizAttempt", back_populates="quiz", cascade="all, delete-orphan")

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False)
    question_text = Column(Text, nullable=False)
    option_a = Column(Text, nullable=False)
    option_b = Column(Text, nullable=False)
    option_c = Column(Text, nullable=False)
    option_d = Column(Text, nullable=False)
    correct_answer = Column(String(1), nullable=False)  # 'A', 'B', 'C', or 'D'
    explanation = Column(Text, nullable=True)

    quiz = relationship("Quiz", back_populates="questions")
    answers = relationship("UserAnswer", back_populates="question", cascade="all, delete-orphan")

class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    quiz_id = Column(Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False)
    total_questions = Column(Integer, nullable=False)
    correct_answers = Column(Integer, nullable=False)
    wrong_answers = Column(Integer, nullable=False)
    unanswered = Column(Integer, nullable=False)
    score = Column(Integer, nullable=False)  # number of correct answers
    percentage = Column(Float, nullable=False)
    time_taken = Column(Integer, default=0)  # in seconds
    completed_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="attempts")
    quiz = relationship("Quiz", back_populates="attempts")
    answers = relationship("UserAnswer", back_populates="attempt", cascade="all, delete-orphan")

class UserAnswer(Base):
    __tablename__ = "user_answers"

    id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(Integer, ForeignKey("quiz_attempts.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    selected_answer = Column(String(1), nullable=True)  # 'A', 'B', 'C', 'D' or None
    is_correct = Column(Boolean, default=False, nullable=False)

    attempt = relationship("QuizAttempt", back_populates="answers")
    question = relationship("Question", back_populates="answers")

# ==========================================
# AUTH HELPERS (BCRYPT & JWT)
# ==========================================
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.utcnow() + expires_delta
    else:
        expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

security = HTTPBearer(auto_error=False)

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security), db: Session = Depends(get_db)) -> User:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_id = int(user_id_str)
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid token. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Administrator privileges required.",
        )
    return current_user

def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security), db: Session = Depends(get_db)) -> Optional[User]:
    if not credentials:
        return None
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        return db.query(User).filter(User.id == user_id).first()
    except Exception:
        return None

# ==========================================
# PYDANTIC SCHEMAS
# ==========================================
class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)
    confirm_password: str = Field(..., min_length=6)
    role: Optional[str] = "STUDENT"

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class DemoLoginRequest(BaseModel):
    role: str = Field(..., pattern="^(STUDENT|ADMIN)$")

class QuestionCreateSchema(BaseModel):
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_answer: str = Field(..., pattern="^[A-Da-d]$")
    explanation: Optional[str] = ""

class QuizCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = ""
    category: str = "Programming"
    difficulty: str = "Medium"
    duration: int = Field(..., ge=1, le=180)  # minutes
    is_published: bool = True
    questions: List[QuestionCreateSchema] = Field(..., min_length=1)

class QuizUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    difficulty: Optional[str] = None
    duration: Optional[int] = None
    is_published: Optional[bool] = None

class SubmitQuizRequest(BaseModel):
    answers: Dict[str, str]  # { "question_id": "A" }
    time_taken: int = 0  # in seconds

class AIAssistantRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None


# ==========================================
# DATABASE SEEDING
# ==========================================
def seed_database(db: Session):
    # Check if admin already exists
    admin = db.query(User).filter(User.email == "admin@quiznova.com").first()
    if not admin:
        admin = User(
            name="Dr. Sarah Vance (Admin)",
            email="admin@quiznova.com",
            hashed_password=hash_password(DEMO_ADMIN_PASSWORD),
            role="ADMIN"
        )
        db.add(admin)

    student = db.query(User).filter(User.email == "student@quiznova.com").first()
    if not student:
        student = User(
            name="Alex Nova (Student)",
            email="student@quiznova.com",
            hashed_password=hash_password(DEMO_STUDENT_PASSWORD),
            role="STUDENT"
        )
        db.add(student)

    # Additional demo students for vibrant leaderboard
    maya = db.query(User).filter(User.email == "maya@quiznova.com").first()
    if not maya:
        maya = User(
            name="Maya Lin",
            email="maya@quiznova.com",
            hashed_password=hash_password(secrets.token_urlsafe(32)),
            role="STUDENT"
        )
        db.add(maya)

    jordan = db.query(User).filter(User.email == "jordan@quiznova.com").first()
    if not jordan:
        jordan = User(
            name="Jordan Lee",
            email="jordan@quiznova.com",
            hashed_password=hash_password(secrets.token_urlsafe(32)),
            role="STUDENT"
        )
        db.add(jordan)

    db.commit()

    # Refresh users to get IDs
    db.refresh(admin)
    db.refresh(student)
    db.refresh(maya)
    db.refresh(jordan)

    # Seed Quizzes if none exist
    if db.query(Quiz).count() == 0:
        # Quiz 1: Python Fundamentals (at least 5 questions, here 7)
        q1 = Quiz(
            title="Python Fundamentals",
            description="Master the core concepts of Python programming: syntax, types, functions, and memory basics.",
            category="Programming",
            difficulty="Easy",
            duration=10,
            is_published=True
        )
        db.add(q1)
        db.flush()

        questions_q1 = [
            Question(
                quiz_id=q1.id,
                question_text="What is the correct file extension for Python files?",
                option_a=".py",
                option_b=".pt",
                option_c=".pyt",
                option_d=".python",
                correct_answer="A",
                explanation=".py is the standard file extension used for Python source code files."
            ),
            Question(
                quiz_id=q1.id,
                question_text="Which keyword is used to declare a function in Python?",
                option_a="func",
                option_b="def",
                option_c="function",
                option_d="define",
                correct_answer="B",
                explanation="The 'def' keyword (short for define) is used to define functions in Python."
            ),
            Question(
                quiz_id=q1.id,
                question_text="What will type([]) evaluate to in Python 3?",
                option_a="<class 'tuple'>",
                option_b="<class 'dict'>",
                option_c="<class 'list'>",
                option_d="<class 'set'>",
                correct_answer="C",
                explanation="Square brackets [] denote an empty list literal in Python."
            ),
            Question(
                quiz_id=q1.id,
                question_text="Which of the following data structures is immutable in Python?",
                option_a="List",
                option_b="Dictionary",
                option_c="Set",
                option_d="Tuple",
                correct_answer="D",
                explanation="Tuples cannot be modified after creation; they are immutable."
            ),
            Question(
                quiz_id=q1.id,
                question_text="How do you write a single-line comment in Python?",
                option_a="// This is a comment",
                option_b="# This is a comment",
                option_c="/* This is a comment */",
                option_d="<!-- This is a comment -->",
                correct_answer="B",
                explanation="The '#' character denotes the start of a single-line comment in Python."
            ),
            Question(
                quiz_id=q1.id,
                question_text="Which built-in function returns the number of items in a collection?",
                option_a="len()",
                option_b="size()",
                option_c="count()",
                option_d="length()",
                correct_answer="A",
                explanation="len() is the standard Python built-in function to obtain collection length."
            ),
            Question(
                quiz_id=q1.id,
                question_text="What is the result of the expression: 2 ** 3?",
                option_a="6",
                option_b="8",
                option_c="9",
                option_d="5",
                correct_answer="B",
                explanation="** is the exponentiation operator in Python. 2 raised to power 3 is 8."
            ),
        ]
        db.add_all(questions_q1)

        # Quiz 2: Web Development Essentials
        q2 = Quiz(
            title="Web Development Essentials",
            description="Test your modern web tech acumen: HTML5 semantic tags, CSS layout engines, and JS runtime basics.",
            category="Web Dev",
            difficulty="Medium",
            duration=8,
            is_published=True
        )
        db.add(q2)
        db.flush()

        questions_q2 = [
            Question(
                quiz_id=q2.id,
                question_text="Which HTML5 tag is semantically best suited for self-contained syndicated content such as blog posts?",
                option_a="<section>",
                option_b="<article>",
                option_c="<aside>",
                option_d="<main>",
                correct_answer="B",
                explanation="<article> represents a self-contained composition that is independently distributable."
            ),
            Question(
                quiz_id=q2.id,
                question_text="What does CSS 'box-sizing: border-box' include in an element's total width and height?",
                option_a="Only Content",
                option_b="Content and Margin",
                option_c="Content, Padding, and Border",
                option_d="Padding, Border, and Margin",
                correct_answer="C",
                explanation="border-box incorporates padding and border within the specified width and height."
            ),
            Question(
                quiz_id=q2.id,
                question_text="Which HTTP status code signifies 'Resource Not Found'?",
                option_a="200",
                option_b="403",
                option_c="404",
                option_d="500",
                correct_answer="C",
                explanation="HTTP 404 indicates that the server cannot locate the requested resource."
            ),
            Question(
                quiz_id=q2.id,
                question_text="In JavaScript, what does '===' compare in addition to values?",
                option_a="Memory address only",
                option_b="Data type and Value (Strict Equality)",
                option_c="Prototype chain only",
                option_d="Scope hierarchy",
                correct_answer="B",
                explanation="=== checks strict equality without type coercion; both type and value must match."
            ),
            Question(
                quiz_id=q2.id,
                question_text="What does CORS stand for in web security?",
                option_a="Cross-Origin Resource Sharing",
                option_b="Central Object Routing System",
                option_c="Cascading Origin Request Server",
                option_d="Client-Oriented Remote Standard",
                correct_answer="A",
                explanation="CORS is Cross-Origin Resource Sharing, a mechanism that allows restricted resources on a web page to be requested from another domain."
            ),
        ]
        db.add_all(questions_q2)

        # Quiz 3: Database & SQL Mastery
        q3 = Quiz(
            title="Database & SQL Mastery",
            description="Deep dive into relational databases, SQL queries, indexes, normalization, and ACID transactions.",
            category="Database",
            difficulty="Hard",
            duration=12,
            is_published=True
        )
        db.add(q3)
        db.flush()

        questions_q3 = [
            Question(
                quiz_id=q3.id,
                question_text="Which SQL clause is used to filter records resulting from a GROUP BY aggregation?",
                option_a="WHERE",
                option_b="HAVING",
                option_c="ORDER BY",
                option_d="LIMIT",
                correct_answer="B",
                explanation="HAVING filters groups created by GROUP BY, whereas WHERE filters individual rows before grouping."
            ),
            Question(
                quiz_id=q3.id,
                question_text="What does the 'A' represent in the database transaction acronym ACID?",
                option_a="Availability",
                option_b="Atomicity",
                option_c="Asynchronous",
                option_d="Authentication",
                correct_answer="B",
                explanation="Atomicity guarantees that all operations within a transaction succeed or all fail together."
            ),
            Question(
                quiz_id=q3.id,
                question_text="Which type of JOIN returns all records from both tables, matching rows where possible and filling with NULL otherwise?",
                option_a="INNER JOIN",
                option_b="LEFT JOIN",
                option_c="RIGHT JOIN",
                option_d="FULL OUTER JOIN",
                correct_answer="D",
                explanation="FULL OUTER JOIN produces the union of records from left and right tables."
            ),
            Question(
                quiz_id=q3.id,
                question_text="Which constraint uniquely identifies each record in a relational database table?",
                option_a="FOREIGN KEY",
                option_b="CHECK",
                option_c="PRIMARY KEY",
                option_d="DEFAULT",
                correct_answer="C",
                explanation="A PRIMARY KEY constraint uniquely identifies each record and does not allow NULL values."
            ),
            Question(
                quiz_id=q3.id,
                question_text="What is the primary benefit of creating an index on a frequently searched column?",
                option_a="Speeds up data retrieval queries",
                option_b="Reduces required disk storage",
                option_c="Accelerates INSERT and UPDATE speeds",
                option_d="Encrypts table contents",
                correct_answer="A",
                explanation="Indexes dramatically improve SELECT lookup speeds using B-Trees, though they slightly overhead writes."
            ),
        ]
        db.add_all(questions_q3)

        # Quiz 4: Draft Quiz (to showcase Admin Publish/Draft management)
        q4 = Quiz(
            title="Cloud Architecture & Microservices",
            description="Explore containerization, serverless functions, orchestration, and distributed systems (Draft).",
            category="DevOps",
            difficulty="Hard",
            duration=15,
            is_published=False  # DRAFT!
        )
        db.add(q4)
        db.flush()

        questions_q4 = [
            Question(
                quiz_id=q4.id,
                question_text="Which tool is an open-source container orchestration engine?",
                option_a="Kubernetes",
                option_b="Vagrant",
                option_c="Nginx",
                option_d="Redis",
                correct_answer="A",
                explanation="Kubernetes automates deployment, scaling, and management of containerized applications."
            ),
            Question(
                quiz_id=q4.id,
                question_text="What does the CAP theorem state regarding distributed data stores?",
                option_a="You can achieve all 3: Consistency, Availability, Partition tolerance",
                option_b="A distributed system can only provide at most two out of three guarantees simultaneously",
                option_c="Performance is always inversely proportional to cost",
                option_d="Cloud security requires three independent authentication keys",
                correct_answer="B",
                explanation="Eric Brewer's CAP theorem states that in the event of network partition, one must trade off between consistency and availability."
            )
        ]
        db.add_all(questions_q4)

        db.commit()

        # Seed realistic demo attempts so leaderboard and stats are immediately exciting!
        # Attempt 1: Maya scored 100% on Python Fundamentals
        att1 = QuizAttempt(
            user_id=maya.id,
            quiz_id=q1.id,
            total_questions=7,
            correct_answers=7,
            wrong_answers=0,
            unanswered=0,
            score=7,
            percentage=100.0,
            time_taken=210,
            completed_at=datetime.datetime.utcnow() - datetime.timedelta(hours=2)
        )
        db.add(att1)

        # Attempt 2: Alex Nova scored 85.7% (6/7) on Python Fundamentals
        att2 = QuizAttempt(
            user_id=student.id,
            quiz_id=q1.id,
            total_questions=7,
            correct_answers=6,
            wrong_answers=1,
            unanswered=0,
            score=6,
            percentage=85.7,
            time_taken=275,
            completed_at=datetime.datetime.utcnow() - datetime.timedelta(hours=1)
        )
        db.add(att2)

        # Attempt 3: Jordan scored 71.4% (5/7) on Python Fundamentals
        att3 = QuizAttempt(
            user_id=jordan.id,
            quiz_id=q1.id,
            total_questions=7,
            correct_answers=5,
            wrong_answers=2,
            unanswered=0,
            score=5,
            percentage=71.4,
            time_taken=340,
            completed_at=datetime.datetime.utcnow() - datetime.timedelta(minutes=45)
        )
        db.add(att3)

        # Attempt 4: Alex Nova scored 100% (5/5) on Web Dev
        att4 = QuizAttempt(
            user_id=student.id,
            quiz_id=q2.id,
            total_questions=5,
            correct_answers=5,
            wrong_answers=0,
            unanswered=0,
            score=5,
            percentage=100.0,
            time_taken=180,
            completed_at=datetime.datetime.utcnow() - datetime.timedelta(minutes=15)
        )
        db.add(att4)

        db.commit()

# ==========================================
# LIFESPAN & APPLICATION CREATION
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create tables and seed data
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_database(db)
    yield
    # Shutdown logic if needed

app = FastAPI(
    title="QuizNova API",
    description="Backend API for QuizNova – Online Quiz & Result System",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# AUTH ENDPOINTS
# ==========================================
@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if payload.password != payload.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match."
        )

    clean_email = payload.email.lower().strip()
    existing_user = db.query(User).filter(User.email == clean_email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists."
        )

    role = payload.role.upper() if payload.role and payload.role.upper() in ["STUDENT", "ADMIN"] else "STUDENT"

    new_user = User(
        name=payload.name.strip(),
        email=clean_email,
        hashed_password=hash_password(payload.password),
        role=role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token(data={"sub": str(new_user.id), "role": new_user.role})

    return {
        "message": "Registration successful!",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": new_user.id,
            "name": new_user.name,
            "email": new_user.email,
            "role": new_user.role
        }
    }

@app.post("/api/auth/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    clean_email = payload.email.lower().strip()
    user = db.query(User).filter(User.email == clean_email).first()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password. Please verify your credentials."
        )

    token = create_access_token(data={"sub": str(user.id), "role": user.role})

    return {
        "message": "Login successful!",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role
        }
    }

@app.post("/api/auth/demo-login")
def demo_login(payload: DemoLoginRequest, db: Session = Depends(get_db)):
    demo_accounts = {
        "STUDENT": ("student@quiznova.com", DEMO_STUDENT_PASSWORD),
        "ADMIN": ("admin@quiznova.com", DEMO_ADMIN_PASSWORD),
    }
    email, password = demo_accounts[payload.role]
    return login(LoginRequest(email=email, password=password), db)

@app.get("/api/auth/me")
def get_my_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    attempts = db.query(QuizAttempt).filter(QuizAttempt.user_id == current_user.id).all()
    total_quizzes = len(attempts)
    avg_score = round(sum(a.percentage for a in attempts) / total_quizzes, 1) if total_quizzes > 0 else 0.0
    best_score = max((a.percentage for a in attempts), default=0.0)

    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role,
        "created_at": current_user.created_at.isoformat(),
        "stats": {
            "quizzes_completed": total_quizzes,
            "average_percentage": avg_score,
            "best_percentage": best_score
        }
    }

@app.get("/api/student/learning-progress")
def get_student_learning_progress(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    attempts = db.query(QuizAttempt).filter(QuizAttempt.user_id == current_user.id).order_by(QuizAttempt.completed_at.desc()).all()
    total_quizzes = len(attempts)
    avg_score = round(sum(a.percentage for a in attempts) / total_quizzes, 1) if total_quizzes > 0 else 0.0
    best_score = max((a.percentage for a in attempts), default=0.0)

    # 1. Continue Learning: Most recent attempt
    continue_learning = None
    if attempts:
        latest = attempts[0]
        continue_learning = {
            "quiz_id": latest.quiz_id,
            "quiz_title": latest.quiz.title if latest.quiz else "Quiz",
            "quiz_category": latest.quiz.category if latest.quiz else "General",
            "quiz_difficulty": latest.quiz.difficulty if latest.quiz else "Medium",
            "percentage": latest.percentage,
            "score": latest.score,
            "total_questions": latest.total_questions,
            "time_taken": latest.time_taken,
            "completed_at": latest.completed_at.isoformat()
        }

    # 2. Weekly Activity (Past 7 days up to today)
    now = datetime.datetime.utcnow()
    days_data = []
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    attempt_dates = set(a.completed_at.date() for a in attempts)

    for i in range(6, -1, -1):
        target_date = (now - datetime.timedelta(days=i)).date()
        day_name = day_names[target_date.weekday()]
        count = sum(1 for a in attempts if a.completed_at.date() == target_date)
        days_data.append({
            "day": day_name,
            "date": target_date.isoformat(),
            "count": count,
            "is_today": (i == 0)
        })

    # 3. Consecutive Learning Streak calculation
    streak = 0
    today = now.date()
    yesterday = today - datetime.timedelta(days=1)
    check_date = today if today in attempt_dates else (yesterday if yesterday in attempt_dates else None)
    if check_date:
        while check_date in attempt_dates:
            streak += 1
            check_date -= datetime.timedelta(days=1)

    # 4. Weekly Goal (Target: 3 quizzes per week)
    start_of_week = (now - datetime.timedelta(days=now.weekday())).date()
    quizzes_this_week = sum(1 for a in attempts if a.completed_at.date() >= start_of_week)
    target_quizzes = 3
    goal_percentage = min(100, round((quizzes_this_week / target_quizzes) * 100))

    return {
        "user_name": current_user.name,
        "first_name": current_user.name.split()[0],
        "quizzes_completed": total_quizzes,
        "average_score": avg_score,
        "best_score": best_score,
        "streak_days": streak,
        "weekly_activity": days_data,
        "weekly_goal": {
            "target": target_quizzes,
            "completed": quizzes_this_week,
            "percentage": goal_percentage
        },
        "continue_learning": continue_learning
    }

@app.post("/api/ai-assistant")
def ai_assistant_chat(payload: AIAssistantRequest, user: Optional[User] = Depends(get_optional_user)):
    msg = payload.message.lower().strip()
    user_name = user.name.split()[0] if user else "Friend"
    is_admin = user and user.role == "ADMIN"

    reply = ""
    actions = []

    # 1. Finding & Exploring Quizzes
    if any(k in msg for k in ["where", "find", "explore", "catalog", "browse", "available", "list"]) and any(k in msg for k in ["quiz", "topic", "course", "lesson", "test", "subject"]):
        reply = (
            f"You can find all available quizzes by clicking **Explore Quizzes** in the left sidebar or scrolling to the quizzes section on your dashboard. "
            f"You can also use the search bar to find specific topics and the category dropdown to filter by Programming, Database, Web Development, or DevOps.\n\n"
            f"📍 **Navigation Path:** Dashboard → Left Sidebar (or Top Nav) → Explore Quizzes → Select Quiz → Start Learning"
        )
        actions = [
            {"label": "Explore Quizzes", "url": "/dashboard.html#available-quizzes-section", "icon": "fa-solid fa-book-open"},
            {"label": "Go to Dashboard", "url": "/dashboard.html", "icon": "fa-solid fa-house"}
        ]

    # 2. How to Start a Quiz
    elif any(k in msg for k in ["how do i start", "how to start", "start a quiz", "begin a quiz", "take a quiz", "launch a quiz", "practice a quiz"]):
        reply = (
            f"Starting a quiz is super easy, {user_name}! Head to **Explore Quizzes**, choose any subject you'd like to practice today, and click **Start Learning**. "
            f"Once launched, questions appear one by one with a live countdown timer in the top bar and an interactive question navigator.\n\n"
            f"📍 **Navigation Path:** Dashboard → Explore Quizzes → Choose Subject (e.g. Python Fundamentals) → Click 'Start Learning'"
        )
        actions = [
            {"label": "Explore Quizzes", "url": "/dashboard.html#available-quizzes-section", "icon": "fa-solid fa-play"},
            {"label": "Go to Dashboard", "url": "/dashboard.html", "icon": "fa-solid fa-house"}
        ]

    # 3. Where are Results / How to See My Results
    elif any(k in msg for k in ["see my result", "view my result", "where are my results", "where is my result", "find result", "see score", "my result", "past result"]):
        reply = (
            f"After completing any quiz, your result appears immediately with your score percentage, time spent, and question-by-question explanations. "
            f"You can also review all your past practice attempts anytime from **My Progress** in the left sidebar or the **Recent Practice Sessions** table on your dashboard.\n\n"
            f"📍 **Navigation Path:** Dashboard → Left Sidebar → My Progress (or Dashboard → Recent Practice Sessions → Review Answers)"
        )
        actions = [
            {"label": "View My Results", "url": "/profile.html", "icon": "fa-solid fa-chart-line"},
            {"label": "Go to Dashboard", "url": "/dashboard.html", "icon": "fa-solid fa-house"}
        ]

    # 4. What Does My Score Mean / Scoring System
    elif any(k in msg for k in ["what does my score mean", "score mean", "how does scoring work", "how is score calculated", "scoring system", "grade system"]):
        reply = (
            f"Your score is calculated as `(Correct Answers / Total Questions) × 100%`:\n"
            f"• **85% – 100% (Mastery / Green):** Excellent grasp of core concepts.\n"
            f"• **60% – 84% (Proficient / Amber):** Solid foundation with room for targeted review.\n"
            f"• **Below 60% (Developing / Coral):** Great opportunity to review answer explanations and practice again!\n\n"
            f"You can retake quizzes anytime to improve your personal best score."
        )
        actions = [
            {"label": "Check My Progress", "url": "/profile.html", "icon": "fa-solid fa-chart-pie"},
            {"label": "Leaderboard", "url": "/leaderboard.html", "icon": "fa-solid fa-trophy"}
        ]

    # 5. Leaderboard / Rankings
    elif any(k in msg for k in ["leaderboard", "rank", "podium", "standing", "who is winning", "top student", "take me to leaderboard"]):
        reply = (
            f"The **Leaderboard** celebrates student achievement across all quizzes! Rankings are ordered by highest score percentage first, then fastest completion time. "
            f"The top 3 achievers are featured on the Gold, Silver, and Bronze podium cards. You can also filter rankings by specific quizzes.\n\n"
            f"📍 **Navigation Path:** Top Navigation (or Left Sidebar) → Leaderboard"
        )
        actions = [
            {"label": "Open Leaderboard", "url": "/leaderboard.html", "icon": "fa-solid fa-trophy"},
            {"label": "Go to Dashboard", "url": "/dashboard.html", "icon": "fa-solid fa-house"}
        ]

    # 6. Profile & Account
    elif any(k in msg for k in ["profile", "account", "my details", "where is profile", "open profile", "take me to profile"]):
        reply = (
            f"Your **Profile** displays your student account information, learning streak, overall average score, personal best score, and your complete history of past quiz attempts with answer reviews.\n\n"
            f"📍 **Navigation Path:** Left Sidebar → My Profile (or Top Right → User Avatar Menu → My Profile)"
        )
        actions = [
            {"label": "Open Profile", "url": "/profile.html", "icon": "fa-solid fa-user"},
            {"label": "Go to Dashboard", "url": "/dashboard.html", "icon": "fa-solid fa-house"}
        ]

    # 7. How the Quiz Timer Works
    elif any(k in msg for k in ["timer", "clock", "time limit", "countdown", "how long", "expire", "run out of time"]):
        reply = (
            f"Each quiz has an estimated time limit in minutes shown on its card. Once you start, a live countdown timer displays in the top bar. "
            f"If time runs low (under 60 seconds), the timer flashes a friendly warning. When time reaches 00:00, QuizNova automatically submits your answers safely so you never lose your hard work!"
        )
        actions = [
            {"label": "Explore Quizzes", "url": "/dashboard.html#available-quizzes-section", "icon": "fa-solid fa-play"}
        ]

    # 8. How to Submit a Quiz
    elif any(k in msg for k in ["how do i submit", "submit a quiz", "how to submit", "finish quiz", "complete quiz"]):
        reply = (
            f"To submit a quiz, click the blue **Submit Quiz** button in the top right header at any time. "
            f"A confirmation modal will appear showing how many questions you have answered versus left blank. Confirming immediately calculates your score and opens your answer breakdown.\n\n"
            f"📍 **Navigation Path:** Quiz Screen → Top Right Header → Click 'Submit Quiz' → Confirm in Dialog"
        )
        actions = [
            {"label": "Explore Quizzes", "url": "/dashboard.html#available-quizzes-section", "icon": "fa-solid fa-book-open"}
        ]

    # 9. Retaking Quizzes
    elif any(k in msg for k in ["retake", "try again", "retry", "repeat", "practice again", "can i retake"]):
        reply = (
            f"Yes! QuizNova is built for continuous practice. You can retake any quiz as many times as you like. "
            f"Your highest score is tracked as your Personal Best on your dashboard and profile.\n\n"
            f"📍 **Navigation Path:** Dashboard → Explore Quizzes (or Continue Learning) → Click 'Practice Again'"
        )
        actions = [
            {"label": "Explore Quizzes", "url": "/dashboard.html#available-quizzes-section", "icon": "fa-solid fa-rotate-right"}
        ]

    # 10. Learning Streak & Weekly Goal
    elif any(k in msg for k in ["streak", "goal", "weekly", "momentum", "daily"]):
        reply = (
            f"QuizNova helps you build a daily learning habit:\n"
            f"• **Learning Streak:** Tracks consecutive active days of completing practice quizzes.\n"
            f"• **Weekly Goal:** Challenges you to complete 3 practice quizzes every week (Monday to Sunday). Track your goal progress in the sidebar widget!\n\n"
            f"📍 **Navigation Path:** Dashboard → Welcome Header (Streak) & Left Sidebar (Weekly Goal Widget)"
        )
        actions = [
            {"label": "Go to Dashboard", "url": "/dashboard.html", "icon": "fa-solid fa-house"},
            {"label": "View My Progress", "url": "/profile.html", "icon": "fa-solid fa-chart-line"}
        ]

    # 11. What Do the Buttons Do / UI Controls
    elif any(k in msg for k in ["button", "palette", "navigator", "previous", "next"]):
        reply = (
            f"Here is what the interface controls do:\n"
            f"• **Question Navigator Palette:** Quick numbered jump bar. Numbers turn Purple when answered and Cyan for the question you are currently on.\n"
            f"• **Previous / Next:** Step through questions sequentially.\n"
            f"• **Exit to Dashboard:** Exits the active session (prompts confirmation first).\n"
            f"• **Theme Toggle:** Switch between Deep Navy and Paper Light modes in the top navbar."
        )
        actions = [
            {"label": "Explore Quizzes", "url": "/dashboard.html#available-quizzes-section", "icon": "fa-solid fa-book-open"}
        ]

    # 12. Theme / Dark Mode / Light Mode
    elif any(k in msg for k in ["theme", "dark mode", "light mode", "navy", "color"]):
        reply = (
            f"You can switch between **Deep Navy** and **Paper Light** modes anytime by clicking the theme toggle button in the top navigation bar. "
            f"Your preference is saved automatically across all pages!"
        )
        actions = [
            {"label": "Go to Dashboard", "url": "/dashboard.html", "icon": "fa-solid fa-house"}
        ]

    # 13. Admin & Instructor Features
    elif any(k in msg for k in ["admin", "instructor", "teacher", "create quiz", "manage quizzes", "submissions"]):
        if is_admin:
            reply = (
                f"As an Instructor/Admin, you can author new quizzes with custom questions and answer explanations, toggle quizzes between Published and Draft, and inspect student submission logs.\n\n"
                f"📍 **Admin Paths:**\n"
                f"• Overview: Admin Panel (`/admin.html`)\n"
                f"• Create Quiz: Admin → Create Quiz (`/create-quiz.html`)\n"
                f"• Manage Quizzes: Admin → Manage Quizzes (`/manage-quizzes.html`)\n"
                f"• Submissions: Admin → Results (`/results.html`)"
            )
            actions = [
                {"label": "Admin Panel", "url": "/admin.html", "icon": "fa-solid fa-chart-line"},
                {"label": "Create New Quiz", "url": "/create-quiz.html", "icon": "fa-solid fa-circle-plus"},
                {"label": "Manage Quizzes", "url": "/manage-quizzes.html", "icon": "fa-solid fa-sliders"}
            ]
        else:
            reply = (
                f"Admin authoring tools are reserved for instructors. You are currently logged in as a Student (`{user_name}`). "
                "If you'd like to explore the instructor tools, sign out and use the Admin Demo Login option on the sign-in page."
            )
            actions = [
                {"label": "Go to Dashboard", "url": "/dashboard.html", "icon": "fa-solid fa-house"},
                {"label": "Sign Out", "url": "/login.html", "icon": "fa-solid fa-arrow-right-from-bracket"}
            ]

    # 14. Friendly Greetings & General Help
    elif any(k in msg for k in ["hello", "hi", "hey", "greeting", "who are you", "what can you do", "help"]):
        reply = (
            f"Hi {user_name}! 👋 I'm QuizNova AI, your personal learning assistant. I can guide you through quizzes, explain how scoring and the timer work, help you find practice topics, or navigate anywhere in QuizNova.\n\n"
            f"Try asking: *'How do I start a quiz?'*, *'Where are my results?'*, or *'What does my score mean?'*"
        )
        actions = [
            {"label": "Explore Quizzes", "url": "/dashboard.html#available-quizzes-section", "icon": "fa-solid fa-book-open"},
            {"label": "Open Leaderboard", "url": "/leaderboard.html", "icon": "fa-solid fa-trophy"},
            {"label": "View My Results", "url": "/profile.html", "icon": "fa-solid fa-chart-line"}
        ]

    # 15. Default Fallback with Navigation Actions
    else:
        reply = (
            f"I'm here to support your learning journey on QuizNova, {user_name}! You can ask me how to start or submit quizzes, where to find your past results, how scoring and the timer work, or where to view the leaderboard."
        )
        actions = [
            {"label": "Explore Quizzes", "url": "/dashboard.html#available-quizzes-section", "icon": "fa-solid fa-book-open"},
            {"label": "Leaderboard", "url": "/leaderboard.html", "icon": "fa-solid fa-trophy"},
            {"label": "My Profile", "url": "/profile.html", "icon": "fa-solid fa-user"}
        ]

    return {
        "reply": reply,
        "actions": actions
    }


# ==========================================
# QUIZ & RESULT ENDPOINTS (STUDENT / PUBLIC)
# ==========================================
@app.get("/api/quizzes")
def get_quizzes(
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user)
):
    query = db.query(Quiz).filter(Quiz.is_published == True)

    if category and category.lower() != "all":
        query = query.filter(Quiz.category.ilike(f"%{category}%"))
    if difficulty and difficulty.lower() != "all":
        query = query.filter(Quiz.difficulty.ilike(f"%{difficulty}%"))
    if search:
        query = query.filter(
            (Quiz.title.ilike(f"%{search}%")) | (Quiz.description.ilike(f"%{search}%"))
        )

    quizzes = query.order_by(Quiz.id.desc()).all()

    # User's attempts for marking completed
    user_attempted_quiz_ids = set()
    user_best_scores = {}
    if user:
        user_attempts = db.query(QuizAttempt).filter(QuizAttempt.user_id == user.id).all()
        for att in user_attempts:
            user_attempted_quiz_ids.add(att.quiz_id)
            if att.quiz_id not in user_best_scores or att.percentage > user_best_scores[att.quiz_id]:
                user_best_scores[att.quiz_id] = att.percentage

    result = []
    for q in quizzes:
        question_count = db.query(Question).filter(Question.quiz_id == q.id).count()
        result.append({
            "id": q.id,
            "title": q.title,
            "description": q.description or "",
            "category": q.category,
            "difficulty": q.difficulty,
            "duration": q.duration,
            "question_count": question_count,
            "is_published": q.is_published,
            "completed": q.id in user_attempted_quiz_ids,
            "best_percentage": user_best_scores.get(q.id, None)
        })

    return result

@app.get("/api/quizzes/{quiz_id}")
def get_quiz_details(quiz_id: int, db: Session = Depends(get_db)):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found.")

    if not quiz.is_published:
        raise HTTPException(status_code=403, detail="This quiz is currently in draft mode and not available.")

    questions = db.query(Question).filter(Question.quiz_id == quiz.id).order_by(Question.id.asc()).all()
    if not questions:
        raise HTTPException(status_code=400, detail="This quiz has no questions yet.")

    return {
        "id": quiz.id,
        "title": quiz.title,
        "description": quiz.description,
        "category": quiz.category,
        "difficulty": quiz.difficulty,
        "duration": quiz.duration,
        "total_questions": len(questions),
        "questions": [
            {
                "id": q.id,
                "question_text": q.question_text,
                "option_a": q.option_a,
                "option_b": q.option_b,
                "option_c": q.option_c,
                "option_d": q.option_d
                # NOTE: correct_answer is explicitly omitted here for security!
            }
            for q in questions
        ]
    }

@app.post("/api/quizzes/{quiz_id}/submit")
def submit_quiz(
    quiz_id: int,
    payload: SubmitQuizRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found.")

    questions = db.query(Question).filter(Question.quiz_id == quiz_id).all()
    total_questions = len(questions)
    if total_questions == 0:
        raise HTTPException(status_code=400, detail="Cannot submit an empty quiz.")

    correct_count = 0
    wrong_count = 0
    unanswered_count = 0

    user_answers_to_save = []

    for q in questions:
        q_id_str = str(q.id)
        selected_raw = payload.answers.get(q_id_str)
        selected = selected_raw.strip().upper() if selected_raw else None

        if selected in ["A", "B", "C", "D"]:
            if selected == q.correct_answer.strip().upper():
                correct_count += 1
                is_correct = True
            else:
                wrong_count += 1
                is_correct = False
        else:
            selected = None
            unanswered_count += 1
            is_correct = False

        user_answers_to_save.append({
            "question_id": q.id,
            "selected_answer": selected,
            "is_correct": is_correct
        })

    score = correct_count
    percentage = round((correct_count / total_questions) * 100, 2)

    # Create Attempt record
    attempt = QuizAttempt(
        user_id=current_user.id,
        quiz_id=quiz.id,
        total_questions=total_questions,
        correct_answers=correct_count,
        wrong_answers=wrong_count,
        unanswered=unanswered_count,
        score=score,
        percentage=percentage,
        time_taken=max(0, payload.time_taken),
        completed_at=datetime.datetime.utcnow()
    )
    db.add(attempt)
    db.flush()

    # Save detailed answers
    for ua in user_answers_to_save:
        answer_record = UserAnswer(
            attempt_id=attempt.id,
            question_id=ua["question_id"],
            selected_answer=ua["selected_answer"],
            is_correct=ua["is_correct"]
        )
        db.add(answer_record)

    db.commit()
    db.refresh(attempt)

    return {
        "message": "Quiz submitted successfully!",
        "attempt_id": attempt.id,
        "score": score,
        "percentage": percentage,
        "correct_answers": correct_count,
        "wrong_answers": wrong_count,
        "unanswered": unanswered_count,
        "total_questions": total_questions,
        "time_taken": attempt.time_taken
    }

@app.get("/api/attempts/{attempt_id}")
def get_attempt_result(
    attempt_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    attempt = db.query(QuizAttempt).filter(QuizAttempt.id == attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt result not found.")

    # Only owner or admin can view
    if attempt.user_id != current_user.id and current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Unauthorized to view this attempt result.")

    quiz = attempt.quiz
    student = attempt.user

    # Fetch answer reviews
    answers = db.query(UserAnswer).filter(UserAnswer.attempt_id == attempt.id).all()
    answers_map = {a.question_id: a for a in answers}

    questions = db.query(Question).filter(Question.quiz_id == quiz.id).order_by(Question.id.asc()).all()
    review = []
    for q in questions:
        ans = answers_map.get(q.id)
        selected = ans.selected_answer if ans else None
        is_correct = ans.is_correct if ans else False

        review.append({
            "question_id": q.id,
            "question_text": q.question_text,
            "option_a": q.option_a,
            "option_b": q.option_b,
            "option_c": q.option_c,
            "option_d": q.option_d,
            "selected_answer": selected,
            "correct_answer": q.correct_answer,
            "is_correct": is_correct,
            "explanation": q.explanation or ""
        })

    return {
        "id": attempt.id,
        "quiz_id": quiz.id,
        "quiz_title": quiz.title,
        "quiz_category": quiz.category,
        "quiz_difficulty": quiz.difficulty,
        "student_name": student.name,
        "student_email": student.email,
        "total_questions": attempt.total_questions,
        "correct_answers": attempt.correct_answers,
        "wrong_answers": attempt.wrong_answers,
        "unanswered": attempt.unanswered,
        "score": attempt.score,
        "percentage": attempt.percentage,
        "time_taken": attempt.time_taken,
        "completed_at": attempt.completed_at.isoformat(),
        "review": review
    }

@app.get("/api/my-attempts")
def get_my_attempts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    attempts = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.user_id == current_user.id)
        .order_by(QuizAttempt.completed_at.desc())
        .all()
    )

    results = []
    for att in attempts:
        results.append({
            "id": att.id,
            "quiz_id": att.quiz_id,
            "quiz_title": att.quiz.title if att.quiz else "Deleted Quiz",
            "quiz_category": att.quiz.category if att.quiz else "General",
            "score": att.score,
            "total_questions": att.total_questions,
            "percentage": att.percentage,
            "time_taken": att.time_taken,
            "completed_at": att.completed_at.isoformat()
        })
    return results

@app.get("/api/leaderboard")
def get_leaderboard(
    quiz_id: Optional[int] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    query = db.query(QuizAttempt)
    if quiz_id:
        query = query.filter(QuizAttempt.quiz_id == quiz_id)

    # Order by highest percentage desc, score desc, time_taken asc (fastest first)
    attempts = (
        query.order_by(
            QuizAttempt.percentage.desc(),
            QuizAttempt.score.desc(),
            QuizAttempt.time_taken.asc(),
            QuizAttempt.completed_at.desc()
        )
        .limit(limit)
        .all()
    )

    leaderboard = []
    for rank, att in enumerate(attempts, start=1):
        leaderboard.append({
            "rank": rank,
            "attempt_id": att.id,
            "student_name": att.user.name if att.user else "Anonymous Student",
            "quiz_title": att.quiz.title if att.quiz else "General Quiz",
            "quiz_category": att.quiz.category if att.quiz else "General",
            "score": att.score,
            "total_questions": att.total_questions,
            "percentage": att.percentage,
            "time_taken": att.time_taken,
            "completed_at": att.completed_at.isoformat()
        })

    # Available quizzes list for filter dropdown
    quizzes = db.query(Quiz).filter(Quiz.is_published == True).all()
    quiz_options = [{"id": q.id, "title": q.title} for q in quizzes]

    return {
        "leaderboard": leaderboard,
        "quizzes": quiz_options
    }

# ==========================================
# ADMIN ENDPOINTS
# ==========================================
@app.get("/api/admin/stats")
def get_admin_stats(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    total_students = db.query(User).filter(User.role == "STUDENT").count()
    total_quizzes = db.query(Quiz).count()
    total_attempts = db.query(QuizAttempt).count()

    all_attempts = db.query(QuizAttempt).all()
    avg_score = round(sum(a.percentage for a in all_attempts) / total_attempts, 1) if total_attempts > 0 else 0.0

    # Recent attempts
    recent = (
        db.query(QuizAttempt)
        .order_by(QuizAttempt.completed_at.desc())
        .limit(6)
        .all()
    )

    recent_list = []
    for att in recent:
        recent_list.append({
            "id": att.id,
            "student_name": att.user.name if att.user else "Unknown",
            "student_email": att.user.email if att.user else "N/A",
            "quiz_title": att.quiz.title if att.quiz else "Unknown Quiz",
            "score": att.score,
            "total_questions": att.total_questions,
            "percentage": att.percentage,
            "completed_at": att.completed_at.isoformat()
        })

    return {
        "total_students": total_students,
        "total_quizzes": total_quizzes,
        "total_attempts": total_attempts,
        "average_score": avg_score,
        "recent_attempts": recent_list
    }

@app.get("/api/admin/quizzes")
def get_all_quizzes_admin(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    quizzes = db.query(Quiz).order_by(Quiz.id.desc()).all()
    results = []
    for q in quizzes:
        q_count = db.query(Question).filter(Question.quiz_id == q.id).count()
        att_count = db.query(QuizAttempt).filter(QuizAttempt.quiz_id == q.id).count()
        results.append({
            "id": q.id,
            "title": q.title,
            "description": q.description,
            "category": q.category,
            "difficulty": q.difficulty,
            "duration": q.duration,
            "is_published": q.is_published,
            "question_count": q_count,
            "attempt_count": att_count,
            "created_at": q.created_at.isoformat()
        })
    return results

@app.post("/api/admin/quizzes", status_code=status.HTTP_201_CREATED)
def create_quiz_admin(
    payload: QuizCreateRequest,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    if len(payload.questions) == 0:
        raise HTTPException(status_code=400, detail="A quiz must have at least one question.")

    new_quiz = Quiz(
        title=payload.title.strip(),
        description=payload.description.strip() if payload.description else "",
        category=payload.category.strip() or "General",
        difficulty=payload.difficulty.strip() or "Medium",
        duration=payload.duration,
        is_published=payload.is_published
    )
    db.add(new_quiz)
    db.flush()

    for item in payload.questions:
        ans = item.correct_answer.strip().upper()
        if ans not in ["A", "B", "C", "D"]:
            raise HTTPException(status_code=400, detail=f"Invalid correct answer '{ans}'. Must be A, B, C, or D.")

        q_record = Question(
            quiz_id=new_quiz.id,
            question_text=item.question_text.strip(),
            option_a=item.option_a.strip(),
            option_b=item.option_b.strip(),
            option_c=item.option_c.strip(),
            option_d=item.option_d.strip(),
            correct_answer=ans,
            explanation=item.explanation.strip() if item.explanation else ""
        )
        db.add(q_record)

    db.commit()
    db.refresh(new_quiz)

    return {
        "message": "Quiz created successfully!",
        "quiz_id": new_quiz.id,
        "title": new_quiz.title,
        "question_count": len(payload.questions)
    }

@app.get("/api/admin/quizzes/{quiz_id}")
def get_single_quiz_admin(
    quiz_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found.")

    questions = db.query(Question).filter(Question.quiz_id == quiz.id).order_by(Question.id.asc()).all()

    return {
        "id": quiz.id,
        "title": quiz.title,
        "description": quiz.description,
        "category": quiz.category,
        "difficulty": quiz.difficulty,
        "duration": quiz.duration,
        "is_published": quiz.is_published,
        "questions": [
            {
                "id": q.id,
                "question_text": q.question_text,
                "option_a": q.option_a,
                "option_b": q.option_b,
                "option_c": q.option_c,
                "option_d": q.option_d,
                "correct_answer": q.correct_answer,
                "explanation": q.explanation or ""
            }
            for q in questions
        ]
    }

@app.put("/api/admin/quizzes/{quiz_id}")
def update_quiz_admin(
    quiz_id: int,
    payload: QuizUpdateRequest,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found.")

    if payload.title is not None:
        quiz.title = payload.title.strip()
    if payload.description is not None:
        quiz.description = payload.description.strip()
    if payload.category is not None:
        quiz.category = payload.category.strip()
    if payload.difficulty is not None:
        quiz.difficulty = payload.difficulty.strip()
    if payload.duration is not None:
        quiz.duration = payload.duration
    if payload.is_published is not None:
        quiz.is_published = payload.is_published

    db.commit()
    db.refresh(quiz)

    return {
        "message": "Quiz updated successfully!",
        "quiz": {
            "id": quiz.id,
            "title": quiz.title,
            "is_published": quiz.is_published
        }
    }

@app.patch("/api/admin/quizzes/{quiz_id}/toggle-publish")
def toggle_publish_quiz(
    quiz_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found.")

    quiz.is_published = not quiz.is_published
    db.commit()
    db.refresh(quiz)

    status_str = "Published" if quiz.is_published else "Draft"
    return {
        "message": f"Quiz is now {status_str}.",
        "is_published": quiz.is_published
    }

@app.delete("/api/admin/quizzes/{quiz_id}")
def delete_quiz_admin(
    quiz_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found.")

    title = quiz.title
    db.delete(quiz)
    db.commit()

    return {"message": f"Quiz '{title}' and all its associated questions and attempts were deleted."}

@app.get("/api/admin/results")
def get_all_results_admin(
    search: Optional[str] = None,
    quiz_id: Optional[int] = None,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    query = db.query(QuizAttempt).join(User).join(Quiz)

    if quiz_id:
        query = query.filter(QuizAttempt.quiz_id == quiz_id)
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (User.name.ilike(search_filter)) |
            (User.email.ilike(search_filter)) |
            (Quiz.title.ilike(search_filter))
        )

    attempts = query.order_by(QuizAttempt.completed_at.desc()).all()

    results = []
    for att in attempts:
        results.append({
            "id": att.id,
            "student_name": att.user.name,
            "student_email": att.user.email,
            "quiz_id": att.quiz.id,
            "quiz_title": att.quiz.title,
            "score": att.score,
            "total_questions": att.total_questions,
            "percentage": att.percentage,
            "time_taken": att.time_taken,
            "completed_at": att.completed_at.isoformat()
        })

    # Return list of quizzes for filter dropdown
    quizzes = db.query(Quiz).all()
    quiz_options = [{"id": q.id, "title": q.title} for q in quizzes]

    return {
        "results": results,
        "quizzes": quiz_options
    }

# ==========================================
# STATIC FILES & ROUTE REDIRECTS
# ==========================================
STATIC_DIR = os.path.join(BASE_DIR, "static")
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, "css"), exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, "js"), exist_ok=True)

# Mount static folder
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def read_root():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.get("/{page_name}.html")
def read_html_page(page_name: str):
    file_path = os.path.join(STATIC_DIR, f"{page_name}.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return RedirectResponse(url="/")

@app.get("/login")
def redirect_login():
    return FileResponse(os.path.join(STATIC_DIR, "login.html"))

@app.get("/register")
def redirect_register():
    return FileResponse(os.path.join(STATIC_DIR, "register.html"))

@app.get("/dashboard")
def redirect_dashboard():
    return FileResponse(os.path.join(STATIC_DIR, "dashboard.html"))

@app.get("/quiz")
def redirect_quiz():
    return FileResponse(os.path.join(STATIC_DIR, "quiz.html"))

@app.get("/result")
def redirect_result():
    return FileResponse(os.path.join(STATIC_DIR, "result.html"))

@app.get("/leaderboard")
def redirect_leaderboard():
    return FileResponse(os.path.join(STATIC_DIR, "leaderboard.html"))

@app.get("/profile")
def redirect_profile():
    return FileResponse(os.path.join(STATIC_DIR, "profile.html"))

@app.get("/admin")
def redirect_admin():
    return FileResponse(os.path.join(STATIC_DIR, "admin.html"))

@app.get("/create-quiz")
def redirect_create_quiz():
    return FileResponse(os.path.join(STATIC_DIR, "create-quiz.html"))

@app.get("/manage-quizzes")
def redirect_manage_quizzes():
    return FileResponse(os.path.join(STATIC_DIR, "manage-quizzes.html"))

@app.get("/results")
def redirect_results():
    return FileResponse(os.path.join(STATIC_DIR, "results.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
