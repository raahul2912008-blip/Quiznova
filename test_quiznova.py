import urllib.request
import json
import os
from dotenv import load_dotenv

BASE = 'http://127.0.0.1:8000'
load_dotenv()

def req(url, data=None, headers=None, method='GET'):
    if headers is None:
        headers = {}
    if data is not None:
        data = json.dumps(data).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode('utf-8'))

print("=== 1. Testing GET /api/quizzes ===")
status, quizzes = req(f"{BASE}/api/quizzes")
print(f"Status: {status}, Quizzes Count: {len(quizzes)}")
assert status == 200 and len(quizzes) >= 3

print("=== 2. Testing Student Login ===")
status, s_res = req(f"{BASE}/api/auth/login", {"email": "student@quiznova.com", "password": os.environ["QUIZNOVA_DEMO_STUDENT_PASSWORD"]}, method="POST")
print(f"Status: {status}, Token: {bool(s_res.get('access_token'))}, Role: {s_res['user']['role']}")
assert status == 200 and s_res['user']['role'] == "STUDENT"
s_token = s_res['access_token']

print("=== 3. Testing Admin Login ===")
status, a_res = req(f"{BASE}/api/auth/login", {"email": "admin@quiznova.com", "password": os.environ["QUIZNOVA_DEMO_ADMIN_PASSWORD"]}, method="POST")
print(f"Status: {status}, Token: {bool(a_res.get('access_token'))}, Role: {a_res['user']['role']}")
assert status == 200 and a_res['user']['role'] == "ADMIN"
a_token = a_res['access_token']

print("=== 4. Testing GET /api/quizzes/1 ===")
status, q1 = req(f"{BASE}/api/quizzes/1")
print(f"Status: {status}, Title: {q1['title']}, Questions: {len(q1['questions'])}")
assert status == 200 and len(q1['questions']) >= 5
assert 'correct_answer' not in q1['questions'][0]  # Secure!

print("=== 5. Testing Quiz Submission ===")
answers = {str(q['id']): "A" for q in q1['questions']}
status, sub_res = req(f"{BASE}/api/quizzes/1/submit", {"answers": answers, "time_taken": 45}, headers={"Authorization": f"Bearer {s_token}"}, method="POST")
print(f"Status: {status}, Score: {sub_res['score']}/{sub_res['total_questions']}, Pct: {sub_res['percentage']}%, Attempt ID: {sub_res['attempt_id']}")
assert status == 200 and sub_res['attempt_id'] > 0

print("=== 6. Testing GET /api/attempts/{id} ===")
status, att_res = req(f"{BASE}/api/attempts/{sub_res['attempt_id']}", headers={"Authorization": f"Bearer {s_token}"})
print(f"Status: {status}, Quiz: {att_res['quiz_title']}, Reviews count: {len(att_res['review'])}")
assert status == 200 and len(att_res['review']) == sub_res['total_questions']

print("=== 7. Testing GET /api/leaderboard ===")
status, lb_res = req(f"{BASE}/api/leaderboard")
print(f"Status: {status}, Leaderboard Entries: {len(lb_res['leaderboard'])}")
assert status == 200 and len(lb_res['leaderboard']) > 0

print("=== 8. Testing Admin Stats ===")
status, stats_res = req(f"{BASE}/api/admin/stats", headers={"Authorization": f"Bearer {a_token}"})
print(f"Status: {status}, Students: {stats_res['total_students']}, Quizzes: {stats_res['total_quizzes']}, Attempts: {stats_res['total_attempts']}")
assert status == 200

print("=== 9. Testing Student Forbidden on Admin Route ===")
status, unauth_res = req(f"{BASE}/api/admin/stats", headers={"Authorization": f"Bearer {s_token}"})
print(f"Status: {status} (Expected 403 Forbidden)")
assert status == 403

print("=== 10. Testing Admin Create Quiz ===")
new_quiz_payload = {
    "title": "Demo Quiz: Cloud & AI",
    "description": "Test quiz created during automated evaluation",
    "category": "DevOps",
    "difficulty": "Medium",
    "duration": 10,
    "is_published": True,
    "questions": [
        {
            "question_text": "What does API stand for in software engineering?",
            "option_a": "Application Programming Interface",
            "option_b": "Automated Protocol Interface",
            "option_c": "Advanced Program Integration",
            "option_d": "Application Process Instruction",
            "correct_answer": "A",
            "explanation": "API stands for Application Programming Interface."
        }
    ]
}
status, create_res = req(f"{BASE}/api/admin/quizzes", new_quiz_payload, headers={"Authorization": f"Bearer {a_token}"}, method="POST")
print(f"Status: {status}, Created Quiz ID: {create_res.get('quiz_id')}")
assert status == 201

print("=== 11. Testing Toggle Publish ===")
created_id = create_res['quiz_id']
status, toggle_res = req(f"{BASE}/api/admin/quizzes/{created_id}/toggle-publish", headers={"Authorization": f"Bearer {a_token}"}, method="PATCH")
print(f"Status: {status}, Toggle Message: {toggle_res['message']}")
assert status == 200 and toggle_res['is_published'] is False

print("=== 12. Testing HTML Pages Serviced ===")
pages = ['/', '/login.html', '/register.html', '/dashboard.html', '/quiz.html', '/result.html', '/leaderboard.html', '/profile.html', '/admin.html', '/create-quiz.html', '/manage-quizzes.html', '/results.html']
for p in pages:
    with urllib.request.urlopen(f"{BASE}{p}") as resp:
        assert resp.status == 200
        print(f"Page OK: {p}")

print("=== 13. Testing GET /api/student/learning-progress ===")
status, lp_res = req(f"{BASE}/api/student/learning-progress", headers={"Authorization": f"Bearer {s_token}"})
print(f"Status: {status}, Streak: {lp_res.get('streak_days')} days, Completed: {lp_res.get('quizzes_completed')}, Weekly Activity: {len(lp_res.get('weekly_activity', []))} days")
assert status == 200 and "streak_days" in lp_res and "weekly_activity" in lp_res and len(lp_res["weekly_activity"]) == 7

print("=== 14. Testing POST /api/ai-assistant ===")
status, ai_res = req(f"{BASE}/api/ai-assistant", {"message": "Where are my quizzes?"}, headers={"Authorization": f"Bearer {s_token}"}, method="POST")
print(f"Status: {status}, AI Reply: {ai_res.get('reply')[:60]}..., Actions: {len(ai_res.get('actions', []))}")
assert status == 200 and "reply" in ai_res and len(ai_res.get("actions", [])) > 0

print("\n>>> ALL 14 INTEGRATION & SECURITY TESTS PASSED PERFECTLY! <<<")
