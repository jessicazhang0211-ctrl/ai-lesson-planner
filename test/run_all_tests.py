import json
import os
import random
import string
import time
import urllib.error
import urllib.request
from datetime import datetime

BASE_URL = os.getenv("TEST_BASE_URL", "http://127.0.0.1:5000")
REPORT_PATH = os.path.join(os.path.dirname(__file__), "TEST_REPORT.md")


def _rand_suffix(n=6):
    pool = string.ascii_lowercase + string.digits
    return "".join(random.choice(pool) for _ in range(n))


def request_json(method, path, data=None, headers=None):
    url = BASE_URL + path
    body = None
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)

    if data is not None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
            parsed = json.loads(raw) if raw else {}
            return resp.getcode(), parsed
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="ignore")
        try:
            parsed = json.loads(raw) if raw else {}
        except Exception:
            parsed = {"raw": raw}
        return e.code, parsed


def assert_true(cond, msg):
    if not cond:
        raise AssertionError(msg)


def run_test(name, fn, results):
    start = time.time()
    try:
        detail = fn()
        cost = round((time.time() - start) * 1000, 2)
        results.append({"name": name, "status": "PASS", "detail": detail, "cost_ms": cost})
        print(f"[PASS] {name} ({cost} ms)")
    except Exception as e:
        cost = round((time.time() - start) * 1000, 2)
        results.append({"name": name, "status": "FAIL", "detail": str(e), "cost_ms": cost})
        print(f"[FAIL] {name} ({cost} ms) -> {e}")


def write_report(results, context):
    total = len(results)
    passed = len([r for r in results if r["status"] == "PASS"])
    failed = total - passed
    lines = []
    lines.append("# 自动化测试报告")
    lines.append("")
    lines.append(f"- 执行时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- 测试地址：{BASE_URL}")
    lines.append(f"- 总用例数：{total}")
    lines.append(f"- 通过：{passed}")
    lines.append(f"- 失败：{failed}")
    lines.append("")
    lines.append("## 关键上下文")
    lines.append("")
    lines.append(f"- 教师测试账号：{context.get('teacher_email', '')}")
    lines.append(f"- 学生测试学号：{context.get('student_stu_id', '')}")
    lines.append(f"- 测试班级ID：{context.get('class_id', '')}")
    lines.append("")
    lines.append("## 用例结果")
    lines.append("")
    for idx, r in enumerate(results, 1):
        lines.append(f"{idx}. {r['name']} - {r['status']} - {r['cost_ms']} ms")
        lines.append(f"   - detail: {r['detail']}")
    lines.append("")
    if failed == 0:
        lines.append("## 结论")
        lines.append("")
        lines.append("本轮自动化测试全部通过，核心业务链路可用。")
    else:
        lines.append("## 结论")
        lines.append("")
        lines.append("本轮自动化测试存在失败项，请根据失败详情逐项修复后复测。")

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    results = []
    ctx = {}

    suffix = _rand_suffix()
    teacher_name = "TestTeacher"
    teacher_email = f"teacher_{suffix}@example.test"
    teacher_password = "Pass123!"
    new_teacher_password = "Pass123!2"

    class_name = f"测试班级_{suffix}"
    student_name = f"学生{suffix}"
    student_phone = "13800000000"

    ctx["teacher_email"] = teacher_email

    teacher_uid_holder = {"value": None}
    teacher_token_holder = {"value": None}
    class_id_holder = {"value": None}
    student_stu_id_holder = {"value": None}

    def test_health_check():
        code, body = request_json("GET", "/api/health")
        assert_true(code == 200, f"health code={code}")
        assert_true(body.get("status") == "ok", f"health body={body}")
        return "health ok"

    def test_teacher_register():
        code, body = request_json("POST", "/api/auth/register", {
            "name": teacher_name,
            "email": teacher_email,
            "password": teacher_password,
            "role": "teacher",
        })
        assert_true(code == 200, f"register code={code}, body={body}")
        data = body.get("data") or {}
        user = data.get("user") or {}
        teacher_uid_holder["value"] = user.get("id")
        assert_true(bool(teacher_uid_holder["value"]), f"missing teacher uid, body={body}")
        return f"uid={teacher_uid_holder['value']}"

    def test_teacher_login():
        code, body = request_json("POST", "/api/auth/login", {
            "email": teacher_email,
            "password": teacher_password,
        })
        assert_true(code == 200, f"login code={code}, body={body}")
        data = body.get("data") or {}
        teacher_token_holder["value"] = data.get("token")
        assert_true(bool(teacher_token_holder["value"]), f"missing token, body={body}")
        return "token ok"

    def test_student_self_register_blocked():
        code, body = request_json("POST", "/api/auth/register", {
            "name": "StudentBlock",
            "email": f"student_block_{suffix}@example.test",
            "password": "123456",
            "role": "student",
        })
        assert_true(code == 403, f"expect 403, got {code}, body={body}")
        return "blocked as expected"

    def test_create_class():
        headers = {
            "Authorization": f"Bearer {teacher_token_holder['value']}",
            "X-User-Id": str(teacher_uid_holder["value"]),
        }
        code, body = request_json("POST", "/api/class/", {
            "name": class_name,
            "desc": "测试描述",
        }, headers=headers)
        assert_true(code == 200, f"create class code={code}, body={body}")
        data = body.get("data") or {}
        class_id_holder["value"] = data.get("id")
        ctx["class_id"] = class_id_holder["value"]
        assert_true(bool(class_id_holder["value"]), f"missing class id, body={body}")
        return f"class_id={class_id_holder['value']}"

    def test_list_classes():
        headers = {
            "Authorization": f"Bearer {teacher_token_holder['value']}",
            "X-User-Id": str(teacher_uid_holder["value"]),
        }
        code, body = request_json("GET", "/api/class/", headers=headers)
        assert_true(code == 200, f"list classes code={code}, body={body}")
        data = body.get("data") or []
        ids = [x.get("id") for x in data if isinstance(x, dict)]
        assert_true(class_id_holder["value"] in ids, f"class {class_id_holder['value']} not found in {ids}")
        return f"total={len(data)}"

    def test_get_class_detail():
        headers = {
            "Authorization": f"Bearer {teacher_token_holder['value']}",
            "X-User-Id": str(teacher_uid_holder["value"]),
        }
        code, body = request_json("GET", f"/api/class/{class_id_holder['value']}", headers=headers)
        assert_true(code == 200, f"get class code={code}, body={body}")
        data = body.get("data") or {}
        assert_true(data.get("id") == class_id_holder["value"], f"unexpected class data={data}")
        return "detail ok"

    def test_list_public_classes():
        code, body = request_json("GET", "/api/class/public")
        assert_true(code == 200, f"public classes code={code}, body={body}")
        data = body.get("data") or []
        assert_true(isinstance(data, list), f"invalid body={body}")
        return f"public_count={len(data)}"

    def test_teacher_overview():
        headers = {"Authorization": f"Bearer {teacher_token_holder['value']}"}
        code, body = request_json("GET", "/api/class/overview", headers=headers)
        assert_true(code == 200, f"overview code={code}, body={body}")
        data = body.get("data") or {}
        assert_true("overview" in data, f"missing overview, body={body}")
        return "overview ok"

    def test_import_students_json():
        headers = {
            "Authorization": f"Bearer {teacher_token_holder['value']}",
            "X-User-Id": str(teacher_uid_holder["value"]),
        }
        code, body = request_json("POST", f"/api/class/{class_id_holder['value']}/import", {
            "students": [
                {
                    "name": student_name,
                    "parent_phone": student_phone,
                    "status": "joined"
                }
            ]
        }, headers=headers)
        assert_true(code == 200, f"import code={code}, body={body}")
        data = body.get("data") or {}
        cls = data.get("class") or {}
        students = cls.get("students") or []
        hit = None
        for s in students:
            if s.get("name") == student_name:
                hit = s
                break
        assert_true(bool(hit), f"imported student not found, students={students}")
        student_stu_id_holder["value"] = hit.get("stu_id")
        ctx["student_stu_id"] = student_stu_id_holder["value"]
        assert_true(bool(student_stu_id_holder["value"]), f"missing auto stu_id, hit={hit}")
        assert_true((data.get("account_created") or 0) >= 1, f"account_created invalid, data={data}")
        return f"stu_id={student_stu_id_holder['value']}"

    student_auth_holder = {"token": None, "uid": None}

    def test_student_login():
        code, body = request_json("POST", "/api/auth/login", {
            "stu_id": student_stu_id_holder["value"],
            "password": "123456",
        })
        assert_true(code == 200, f"student login code={code}, body={body}")
        data = body.get("data") or {}
        user = data.get("user") or {}
        assert_true(user.get("role") == "student", f"not student role, user={user}")
        token = data.get("token")
        assert_true(bool(token), f"missing student token, body={body}")
        student_auth_holder["token"] = token
        student_auth_holder["uid"] = user.get("id")
        assert_true(bool(student_auth_holder["uid"]), f"missing student uid, user={user}")
        assert_true(data.get("must_change_password") is True, f"must_change_password should be true, body={body}")
        return "student login ok (must change password)"

    def test_student_assignments():
        headers = {"Authorization": f"Bearer {student_auth_holder['token']}"}
        code, body = request_json("GET", "/api/student/assignments", headers=headers)
        assert_true(code == 403, f"student assignments code={code}, body={body}")
        data = body.get("data") or {}
        assert_true(data.get("must_change_password") is True, f"missing must_change_password flag, body={body}")
        return "blocked before password change"

    student_new_password = "Student123!"

    def test_student_change_password():
        headers = {"X-User-Id": str(student_auth_holder["uid"])}
        code, body = request_json("POST", "/api/user/change-password", {
            "current_password": "123456",
            "new_password": student_new_password,
        }, headers=headers)
        assert_true(code == 200, f"student change pwd code={code}, body={body}")

        code2, body2 = request_json("POST", "/api/auth/login", {
            "stu_id": student_stu_id_holder["value"],
            "password": student_new_password,
        })
        assert_true(code2 == 200, f"student relogin code={code2}, body={body2}")
        data2 = body2.get("data") or {}
        student_auth_holder["token"] = data2.get("token")
        assert_true(bool(student_auth_holder["token"]), f"missing token after student relogin, body={body2}")
        assert_true(data2.get("must_change_password") is False, f"must_change_password should be false, body={body2}")
        return "student password changed and relogin ok"

    def test_student_assignments_after_change():
        headers = {"Authorization": f"Bearer {student_auth_holder['token']}"}
        code, body = request_json("GET", "/api/student/assignments", headers=headers)
        assert_true(code == 200, f"student assignments(after change) code={code}, body={body}")
        data = body.get("data")
        if isinstance(data, list):
            return f"assignments={len(data)}"
        # Backend ok() serializes empty list as {}; treat as empty set.
        assert_true(isinstance(data, dict), f"assignments invalid body={body}")
        return "assignments=0"

    def test_get_me():
        headers = {"X-User-Id": str(teacher_uid_holder["value"])}
        code, body = request_json("GET", "/api/user/me", headers=headers)
        assert_true(code == 200, f"get me code={code}, body={body}")
        data = body.get("data") or {}
        assert_true(data.get("email") == teacher_email, f"unexpected me data={data}")
        return "get me ok"

    def test_update_me():
        headers = {"X-User-Id": str(teacher_uid_holder["value"])}
        code, body = request_json("PATCH", "/api/user/me", {
            "nickname": f"nick_{suffix}",
            "school": "Test School",
            "major": "Education",
            "job_title": "Teacher",
        }, headers=headers)
        assert_true(code == 200, f"update me code={code}, body={body}")
        return "update me ok"

    def test_change_password_and_relogin():
        headers = {"X-User-Id": str(teacher_uid_holder["value"])}
        code, body = request_json("POST", "/api/user/change-password", {
            "current_password": teacher_password,
            "new_password": new_teacher_password,
        }, headers=headers)
        assert_true(code == 200, f"change pwd code={code}, body={body}")

        code2, body2 = request_json("POST", "/api/auth/login", {
            "email": teacher_email,
            "password": new_teacher_password,
        })
        assert_true(code2 == 200, f"relogin code={code2}, body={body2}")
        return "password changed and relogin ok"

    test_cases = [
        ("health_check", test_health_check),
        ("teacher_register", test_teacher_register),
        ("teacher_login", test_teacher_login),
        ("student_self_register_blocked", test_student_self_register_blocked),
        ("create_class", test_create_class),
        ("list_classes", test_list_classes),
        ("get_class_detail", test_get_class_detail),
        ("list_public_classes", test_list_public_classes),
        ("teacher_overview", test_teacher_overview),
        ("import_students_json", test_import_students_json),
        ("student_login", test_student_login),
        ("student_assignments", test_student_assignments),
        ("student_change_password", test_student_change_password),
        ("student_assignments_after_change", test_student_assignments_after_change),
        ("get_me", test_get_me),
        ("update_me", test_update_me),
        ("change_password_and_relogin", test_change_password_and_relogin),
    ]

    for name, fn in test_cases:
        run_test(name, fn, results)

    write_report(results, ctx)

    failed_count = len([r for r in results if r["status"] == "FAIL"])
    print("\n==============================")
    print(f"TOTAL: {len(results)}, PASS: {len(results) - failed_count}, FAIL: {failed_count}")
    print(f"REPORT: {REPORT_PATH}")
    print("==============================")

    if failed_count > 0:
        raise SystemExit(1)
