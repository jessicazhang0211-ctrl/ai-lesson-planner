from flask import Blueprint, g, request
from app.utils.auth import token_required
from app.utils.response import ok, err
from app.extensions import db
from app.models.student_profile import StudentProfile
from app.models.resource_publish import ResourcePublish
from app.models.resource_assignment import ResourceAssignment
from app.models.exercise_submission import ExerciseSubmission
from app.models.lesson import Lesson
from app.models.exercise import Exercise
from app.config import Config
import json
import datetime

try:
    import google.generativeai as genai
except Exception:
    genai = None

bp = Blueprint("student", __name__, url_prefix="/api/student")

if genai and Config.GEMINI_API_KEY:
    genai.configure(api_key=Config.GEMINI_API_KEY)


def _load_ids(raw):
    try:
        return json.loads(raw) if raw else []
    except Exception:
        return []


def _normalize_answer(v):
    if v is None:
        return ""
    if isinstance(v, list):
        return [str(x).strip().lower() for x in v]
    return str(v).strip().lower()


def _grade_objective(q, user_answer):
    qtype = (q.get("type") or "").lower()
    answer = q.get("answer")
    if qtype in ("single", "true_false"):
        return _normalize_answer(user_answer) == _normalize_answer(answer)
    if qtype == "multi":
        ua = _normalize_answer(user_answer)
        an = _normalize_answer(answer)
        if not isinstance(ua, list):
            ua = [x for x in str(user_answer).replace(" ", "").split(",") if x]
            ua = [x.lower() for x in ua]
        if not isinstance(an, list):
            an = [x for x in str(answer).replace(" ", "").split(",") if x]
            an = [x.lower() for x in an]
        return sorted(ua) == sorted(an)
    if qtype == "fill":
        ua = _normalize_answer(user_answer)
        an = _normalize_answer(answer)
        if isinstance(an, list):
            if not isinstance(ua, list):
                ua = [x.strip().lower() for x in str(user_answer).split(",")]
            return ua == an
        return ua == an
    return None


def _extract_json(text: str):
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(cleaned)
    except Exception:
        pass
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(cleaned[start:end + 1])
        except Exception:
            return None
    return None


def _type_label(t: str):
    t = (t or "").lower()
    return {
        "single": "单选",
        "multi": "多选",
        "true_false": "判断",
        "fill": "填空",
        "short": "简答",
        "essay": "简答"
    }.get(t, "其他")


def _rule_based_analysis(avg_score_all, wrong_rate_map):
    if wrong_rate_map:
        worst = max(wrong_rate_map.items(), key=lambda x: x[1])[0]
        weak_spot = f"{_type_label(worst)}题错误率偏高"
    else:
        weak_spot = "暂无明显薄弱点"

    if avg_score_all is None:
        study_state = "数据不足"
        study_tip = "完成更多作业后再进行分析"
    elif avg_score_all >= 85:
        study_state = "表现优秀"
        study_tip = "保持节奏，尝试提高综合题"
    elif avg_score_all >= 70:
        study_state = "稳定提升"
        study_tip = "建议巩固错题题型"
    else:
        study_state = "需要加强"
        study_tip = "优先补齐基础题型"

    return {
        "weak_spot": weak_spot,
        "study_state": study_state,
        "study_tip": study_tip
    }


def _ai_analysis(summary_text: str):
    if not genai or not Config.GEMINI_API_KEY:
        return None
    if not summary_text:
        return None
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        prompt = (
            "你是教育数据分析助手。请根据以下学生作业表现摘要，输出 JSON，格式为："
            "{\"weak_spot\":\"...\",\"study_state\":\"...\",\"study_tip\":\"...\"}\n"
            "仅输出 JSON，不要额外解释。\n\n"
            f"摘要：{summary_text}"
        )
        response = model.generate_content(prompt)
        data = _extract_json(getattr(response, "text", "") or "")
        if isinstance(data, dict) and all(k in data for k in ("weak_spot", "study_state", "study_tip")):
            return data
    except Exception:
        return None
    return None


@bp.route("/ping", methods=["GET"])
def ping():
    return ok({"status": "ok"})


@bp.route("/assignments", methods=["GET"])
@token_required
def list_assignments():
    user_id = int(getattr(g, "current_user_id", 0) or 0)
    if not user_id:
        return err("missing user", http_status=401)

    profile = StudentProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        return err("student profile not found", http_status=404)

    pubs = ResourcePublish.query.filter_by(class_id=profile.class_id, revoked=False).order_by(ResourcePublish.created_at.desc()).all()
    pub_ids = [p.id for p in pubs]
    if not pub_ids:
        return ok([])

    assignments = ResourceAssignment.query.filter(ResourceAssignment.publish_id.in_(pub_ids), ResourceAssignment.student_id == profile.student_id).all()
    assignment_map = {a.publish_id: a for a in assignments}

    lesson_ids = [p.resource_id for p in pubs if p.resource_type == "lesson"]
    exercise_ids = [p.resource_id for p in pubs if p.resource_type == "exercise"]
    lessons = {l.id: l for l in Lesson.query.filter(Lesson.id.in_(lesson_ids)).all()} if lesson_ids else {}
    exercises = {e.id: e for e in Exercise.query.filter(Exercise.id.in_(exercise_ids)).all()} if exercise_ids else {}

    result = []
    for p in pubs:
        ids = _load_ids(p.student_ids)
        if profile.student_id not in ids:
            continue
        assignment = assignment_map.get(p.id)
        title = lessons.get(p.resource_id).title if p.resource_type == "lesson" else exercises.get(p.resource_id).title
        result.append({
            "publish_id": p.id,
            "resource_type": p.resource_type,
            "resource_id": p.resource_id,
            "title": title or "",
            "created_at": p.created_at.strftime("%Y-%m-%d %H:%M:%S") if p.created_at else "",
            "status": assignment.status if assignment else "assigned"
        })

    return ok(result)


@bp.route("/exercises/<int:publish_id>", methods=["GET"])
@token_required
def get_exercise(publish_id: int):
    user_id = int(getattr(g, "current_user_id", 0) or 0)
    if not user_id:
        return err("missing user", http_status=401)

    profile = StudentProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        return err("student profile not found", http_status=404)

    pub = ResourcePublish.query.get(publish_id)
    if not pub or pub.revoked or pub.class_id != profile.class_id or pub.resource_type != "exercise":
        return err("publish not found", http_status=404)

    ids = _load_ids(pub.student_ids)
    if profile.student_id not in ids:
        return err("not allowed", http_status=403)

    exercise = Exercise.query.get(pub.resource_id)
    if not exercise or not exercise.content_json:
        return err("exercise format not supported", http_status=400)

    try:
        data = json.loads(exercise.content_json)
    except Exception:
        return err("invalid exercise format", http_status=400)

    submission = ExerciseSubmission.query.filter_by(publish_id=pub.id, student_id=profile.student_id).first()
    assignment = ResourceAssignment.query.filter_by(publish_id=pub.id, student_id=profile.student_id).first()
    draft_answers = {}
    submission_status = ""
    auto_result = {}
    auto_score = None
    teacher_score = None
    total_score = None
    if submission and submission.answers:
        try:
            draft_answers = json.loads(submission.answers)
        except Exception:
            draft_answers = {}
        submission_status = submission.status or ""
        auto_score = submission.auto_score
        teacher_score = submission.teacher_score
        total_score = submission.total_score
        if submission.auto_result:
            try:
                auto_result = json.loads(submission.auto_result)
            except Exception:
                auto_result = {}

    # strip answers
    questions = []
    for q in data.get("questions", []):
        q2 = {k: v for k, v in q.items() if k != "answer"}
        questions.append(q2)

    return ok({
        "publish_id": pub.id,
        "title": exercise.title,
        "questions": questions,
        "draft_answers": draft_answers,
        "assignment_status": assignment.status if assignment else "assigned",
        "submission_status": submission_status,
        "auto_result": auto_result,
        "auto_score": auto_score,
        "teacher_score": teacher_score,
        "total_score": total_score
    })


@bp.route("/exercises/<int:publish_id>/save", methods=["POST"])
@token_required
def save_exercise(publish_id: int):
    user_id = int(getattr(g, "current_user_id", 0) or 0)
    if not user_id:
        return err("missing user", http_status=401)

    profile = StudentProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        return err("student profile not found", http_status=404)

    pub = ResourcePublish.query.get(publish_id)
    if not pub or pub.revoked or pub.class_id != profile.class_id or pub.resource_type != "exercise":
        return err("publish not found", http_status=404)

    ids = _load_ids(pub.student_ids)
    if profile.student_id not in ids:
        return err("not allowed", http_status=403)

    data = request.get_json(silent=True) or {}
    answers = data.get("answers") or {}

    submission = ExerciseSubmission.query.filter_by(publish_id=pub.id, student_id=profile.student_id).first()
    assignment = ResourceAssignment.query.filter_by(publish_id=pub.id, student_id=profile.student_id).first()
    if assignment and assignment.status == "completed":
        return err("assignment already completed", http_status=400)

    if not submission:
        submission = ExerciseSubmission(publish_id=pub.id, student_id=profile.student_id)
        db.session.add(submission)

    submission.answers = json.dumps(answers, ensure_ascii=False)
    submission.status = "saved"
    db.session.commit()

    if assignment and assignment.status != "completed":
        assignment.status = "saved"
        db.session.commit()

    return ok({"status": "saved"})


@bp.route("/exercises/<int:publish_id>/submit", methods=["POST"])
@token_required
def submit_exercise(publish_id: int):
    user_id = int(getattr(g, "current_user_id", 0) or 0)
    if not user_id:
        return err("missing user", http_status=401)

    profile = StudentProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        return err("student profile not found", http_status=404)

    pub = ResourcePublish.query.get(publish_id)
    if not pub or pub.revoked or pub.class_id != profile.class_id or pub.resource_type != "exercise":
        return err("publish not found", http_status=404)

    ids = _load_ids(pub.student_ids)
    if profile.student_id not in ids:
        return err("not allowed", http_status=403)

    exercise = Exercise.query.get(pub.resource_id)
    if not exercise or not exercise.content_json:
        return err("exercise format not supported", http_status=400)

    data = request.get_json(silent=True) or {}
    answers = data.get("answers") or {}

    try:
        structured = json.loads(exercise.content_json)
    except Exception:
        return err("invalid exercise format", http_status=400)

    questions = structured.get("questions", [])
    auto_score = 0
    auto_result = {}
    has_subjective = False

    for q in questions:
        qid = q.get("id")
        qtype = (q.get("type") or "").lower()
        score = int(q.get("score") or 0)
        if qtype in ("short", "essay"):
            has_subjective = True
            auto_result[qid] = "pending"
            continue
        ok_flag = _grade_objective(q, answers.get(qid))
        if ok_flag is True:
            auto_score += score
        auto_result[qid] = "correct" if ok_flag else "wrong"

    submission = ExerciseSubmission.query.filter_by(publish_id=pub.id, student_id=profile.student_id).first()
    if not submission:
        submission = ExerciseSubmission(publish_id=pub.id, student_id=profile.student_id)
        db.session.add(submission)

    submission.answers = json.dumps(answers, ensure_ascii=False)
    submission.auto_result = json.dumps(auto_result, ensure_ascii=False)
    submission.auto_score = auto_score
    submission.teacher_score = submission.teacher_score or 0
    submission.total_score = (auto_score + (submission.teacher_score or 0))
    submission.status = "pending_review" if has_subjective else "graded"

    db.session.commit()

    assignment = ResourceAssignment.query.filter_by(publish_id=pub.id, student_id=profile.student_id).first()
    if assignment:
        assignment.status = "completed"
        assignment.score = submission.total_score
        assignment.completed_at = assignment.completed_at or submission.updated_at
        db.session.commit()

    return ok({
        "auto_score": auto_score,
        "auto_result": auto_result,
        "status": submission.status,
        "total_score": submission.total_score
    })


@bp.route("/lessons", methods=["GET"])
@token_required
def list_lessons():
    user_id = int(getattr(g, "current_user_id", 0) or 0)
    if not user_id:
        return err("missing user", http_status=401)

    profile = StudentProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        return err("student profile not found", http_status=404)

    pubs = ResourcePublish.query.filter_by(class_id=profile.class_id, revoked=False, resource_type="lesson") \
        .order_by(ResourcePublish.created_at.desc()).all()

    result = []
    lesson_ids = [p.resource_id for p in pubs]
    lessons = {l.id: l for l in Lesson.query.filter(Lesson.id.in_(lesson_ids)).all()} if lesson_ids else {}

    for p in pubs:
        ids = _load_ids(p.student_ids)
        if profile.student_id not in ids:
            continue
        l = lessons.get(p.resource_id)
        if not l:
            continue
        content = l.description or ""
        if content.startswith("__META__"):
            try:
                meta_str, real_content = content.split("__\n", 1)
                content = real_content
            except Exception:
                pass
        result.append({
            "id": l.id,
            "title": l.title,
            "content": content,
            "created_at": l.created_at.strftime("%Y-%m-%d %H:%M:%S") if l.created_at else "",
            "published_at": p.created_at.strftime("%Y-%m-%d %H:%M:%S") if p.created_at else ""
        })

    return ok(result)


@bp.route("/scores", methods=["GET"])
@token_required
def list_scores():
    user_id = int(getattr(g, "current_user_id", 0) or 0)
    if not user_id:
        return err("missing user", http_status=401)

    profile = StudentProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        return err("student profile not found", http_status=404)

    pubs = ResourcePublish.query.filter_by(class_id=profile.class_id, revoked=False, resource_type="exercise") \
        .order_by(ResourcePublish.created_at.desc()).all()
    pub_ids = [p.id for p in pubs]
    if not pub_ids:
        return ok([])

    assignments = ResourceAssignment.query.filter(ResourceAssignment.publish_id.in_(pub_ids), ResourceAssignment.student_id == profile.student_id).all()
    assignment_map = {a.publish_id: a for a in assignments}

    exercise_ids = [p.resource_id for p in pubs]
    exercises = {e.id: e for e in Exercise.query.filter(Exercise.id.in_(exercise_ids)).all()} if exercise_ids else {}

    result = []
    for p in pubs:
        ids = _load_ids(p.student_ids)
        if profile.student_id not in ids:
            continue
        a = assignment_map.get(p.id)
        e = exercises.get(p.resource_id)
        result.append({
            "publish_id": p.id,
            "title": e.title if e else "",
            "status": a.status if a else "assigned",
            "score": a.score if a else None,
            "completed_at": a.completed_at.strftime("%Y-%m-%d %H:%M:%S") if a and a.completed_at else "",
            "published_at": p.created_at.strftime("%Y-%m-%d %H:%M:%S") if p.created_at else ""
        })

    return ok(result)


@bp.route("/overview", methods=["GET"])
@token_required
def overview():
    user_id = int(getattr(g, "current_user_id", 0) or 0)
    if not user_id:
        return err("missing user", http_status=401)

    profile = StudentProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        return err("student profile not found", http_status=404)

    pubs = ResourcePublish.query.filter_by(class_id=profile.class_id, revoked=False, resource_type="exercise").all()
    pub_ids = [p.id for p in pubs]
    assignments = ResourceAssignment.query.filter(
        ResourceAssignment.publish_id.in_(pub_ids),
        ResourceAssignment.student_id == profile.student_id
    ).all() if pub_ids else []

    total = len(assignments)
    completed_list = [a for a in assignments if a.status == "completed"]
    completed = len(completed_list)
    submission_rate = int(round((completed / total) * 100)) if total else 0

    scores_all = [a.score for a in assignments if a.score is not None]
    avg_score_all = int(round(sum(scores_all) / len(scores_all))) if scores_all else None

    now = datetime.datetime.now()
    week_start = now - datetime.timedelta(days=7)
    scores_week = [a.score for a in assignments if a.score is not None and (a.completed_at or a.created_at) and (a.completed_at or a.created_at) >= week_start]
    avg_score_week = int(round(sum(scores_week) / len(scores_week))) if scores_week else None

    latest_score = None
    completed_with_time = [a for a in assignments if a.score is not None]
    if completed_with_time:
        completed_with_time.sort(key=lambda x: x.completed_at or x.created_at, reverse=True)
        latest_score = completed_with_time[0].score

    trend_items = []
    if completed_with_time:
        completed_with_time.sort(key=lambda x: x.completed_at or x.created_at)
        for a in completed_with_time[-10:]:
            dt = a.completed_at or a.created_at
            label = dt.strftime("%m-%d") if dt else ""
            trend_items.append({"label": label, "score": a.score})

    # weak point analysis
    wrong_total_by_type = {}
    total_by_type = {}
    if pub_ids:
        submissions = (ExerciseSubmission.query
            .filter(ExerciseSubmission.publish_id.in_(pub_ids), ExerciseSubmission.student_id == profile.student_id)
            .order_by(ExerciseSubmission.updated_at.desc())
            .limit(10)
            .all())
        pub_map = {p.id: p for p in pubs}
        exercise_ids = [p.resource_id for p in pubs]
        exercises = {e.id: e for e in Exercise.query.filter(Exercise.id.in_(exercise_ids)).all()} if exercise_ids else {}

        for s in submissions:
            if not s.auto_result:
                continue
            pub = pub_map.get(s.publish_id)
            if not pub:
                continue
            ex = exercises.get(pub.resource_id)
            if not ex or not ex.content_json:
                continue
            try:
                structured = json.loads(ex.content_json)
                auto_result = json.loads(s.auto_result)
            except Exception:
                continue
            for q in structured.get("questions", []):
                qid = q.get("id")
                qtype = (q.get("type") or "").lower()
                if qtype in ("short", "essay"):
                    continue
                total_by_type[qtype] = total_by_type.get(qtype, 0) + 1
                if auto_result.get(qid) == "wrong":
                    wrong_total_by_type[qtype] = wrong_total_by_type.get(qtype, 0) + 1

    wrong_rate_map = {}
    for k, total_cnt in total_by_type.items():
        wrong_cnt = wrong_total_by_type.get(k, 0)
        if total_cnt:
            wrong_rate_map[k] = wrong_cnt / total_cnt

    analysis = _rule_based_analysis(avg_score_all, wrong_rate_map)
    summary_text = (
        f"提交率{submission_rate}%，总平均分{avg_score_all if avg_score_all is not None else '无'}，"
        f"本周平均分{avg_score_week if avg_score_week is not None else '无'}，"
        f"错题比例{ {k: round(v,2) for k,v in wrong_rate_map.items()} }"
    )
    ai_result = _ai_analysis(summary_text)
    if ai_result:
        analysis = ai_result

    return ok({
        "todo": max(total - completed, 0),
        "completed": completed,
        "avg_score": avg_score_all,
        "latest_score": latest_score,
        "submission_rate": submission_rate,
        "avg_score_all": avg_score_all,
        "avg_score_week": avg_score_week,
        "trend": trend_items,
        "analysis": analysis
    })
