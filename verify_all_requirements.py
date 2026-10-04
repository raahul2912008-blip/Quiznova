import urllib.request
import json
import os
from dotenv import load_dotenv

BASE = "http://127.0.0.1:8000"
load_dotenv()

def get_json(url, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode())

def post_json(url, data, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode())

print("--- 1. Testing Student Login & Learning Progress ---")
status, login_res = post_json(f"{BASE}/api/auth/login", {"email": "student@quiznova.com", "password": os.environ["QUIZNOVA_DEMO_STUDENT_PASSWORD"]})
assert status == 200
token = login_res["access_token"]
user_name = login_res["user"]["name"]
print(f"Logged in: {user_name}, Token acquired")

status, progress_data = get_json(f"{BASE}/api/student/learning-progress", token)
assert status == 200
print(f"User: {progress_data['user_name']}, First Name: {progress_data['first_name']}")
print(f"Quizzes completed: {progress_data['quizzes_completed']}, Avg: {progress_data['average_score']}%, Best: {progress_data['best_score']}%")
print(f"Streak: {progress_data['streak_days']} days")
print(f"Weekly Goal: {progress_data['weekly_goal']['completed']} of {progress_data['weekly_goal']['target']} ({progress_data['weekly_goal']['percentage']}%)")
assert len(progress_data["weekly_activity"]) == 7
print(f"Weekly Activity days: {[d['day'] for d in progress_data['weekly_activity']]}")
assert progress_data["continue_learning"] is not None
print(f"Continue Learning: {progress_data['continue_learning']['quiz_title']} ({progress_data['continue_learning']['percentage']}%)")

print("\n--- 2. Testing AI Assistant Knowledge Base & Website Awareness ---")
test_questions = [
    ("Where are my quizzes?", ["Explore Quizzes", "/dashboard.html#available-quizzes-section"]),
    ("How do I start a quiz?", ["Explore Quizzes", "/dashboard.html#available-quizzes-section"]),
    ("Where can I see my result?", ["View My Results", "/profile.html"]),
    ("Where is the leaderboard?", ["Open Leaderboard", "/leaderboard.html"]),
    ("Where can I see my profile?", ["Open Profile", "/profile.html"]),
    ("What does my score mean?", ["Check My Progress", "/profile.html"]),
    ("How does the timer work?", ["Explore Quizzes", "/dashboard.html#available-quizzes-section"]),
    ("How do I submit a quiz?", ["Explore Quizzes", "/dashboard.html#available-quizzes-section"]),
    ("Can I retake a quiz?", ["Explore Quizzes", "/dashboard.html#available-quizzes-section"]),
    ("What is my streak?", ["Go to Dashboard", "/dashboard.html"]),
    ("Take me to leaderboard", ["Open Leaderboard", "/leaderboard.html"]),
]

for question, expected_action in test_questions:
    status, ai_res = post_json(f"{BASE}/api/ai-assistant", {"message": question}, token)
    assert status == 200
    reply = ai_res["reply"]
    actions = ai_res.get("actions", [])
    print(f"\nQ: {question}")
    print(f"A snippet: {reply[:100]}...")
    action_labels = [a["label"] for a in actions]
    action_urls = [a["url"] for a in actions]
    print(f"Actions: {action_labels} -> {action_urls}")
    assert len(reply) > 30, f"Reply too short for: {question}"
    if expected_action:
        label, url = expected_action
        assert any(label in a["label"] for a in actions), f"Expected action '{label}' not found in {action_labels}"
        assert any(url in a["url"] for a in actions), f"Expected URL '{url}' not found in {action_urls}"

print("\n--- 3. Testing Public Pages Availability ---")
pages = [
    "/dashboard.html",
    "/leaderboard.html",
    "/profile.html",
    "/quiz.html",
    "/result.html",
    "/login.html",
    "/register.html",
    "/admin.html",
    "/create-quiz.html",
    "/manage-quizzes.html",
    "/results.html"
]
for p in pages:
    req = urllib.request.Request(f"{BASE}{p}")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        html = resp.read().decode()
        assert "QuizNova" in html
        assert "style.css" in html
    print(f"Verified page: {p} (200 OK)")

print("\n==========================================")
print("SUCCESS: ALL USER REQUIREMENTS VERIFIED!")
print("==========================================")
