import json
import hashlib

from flask import g, request

from app.extensions import db
from app.models.classroom import Classroom, Student
from app.models.exercise import Exercise
from app.models.exercise_submission import ExerciseSubmission
from app.models.resource_assignment import ResourceAssignment
from app.models.resource_publish import ResourcePublish
from app.services.ai_service import ai_service
from app.utils.auth import token_required
from app.utils.response import err, ok

from .blueprint import bp


_REVIEW_AI_SUMMARY_CACHE = {}


def _normalize_lang(lang):
    return "en" if str(lang or "zh").lower().startswith("en") else "zh"


def _safe_json_loads(raw, default):
    try:
        return json.loads(raw or "")
    except Exception:
        return default


def _build_local_review_summary(exercise, structured, submission, lang="zh"):
    lang = _normalize_lang(lang)
    questions = structured.get("questions") or []
    total_questions = len(questions)
    subjective_count = 0
    objective_count = 0
    key_points = []

    for q in questions:
        qtype = str((q or {}).get("type") or "").lower()
        if qtype in ("short", "essay"):
            subjective_count += 1
        else:
            objective_count += 1
        stem = str((q or {}).get("stem") or "").strip()
        if stem:
            key_points.append(stem[:28])

    answers = _safe_json_loads(submission.answers, {})
    has_answer = sum(1 for v in (answers or {}).values() if v not in (None, "", [], {}))
    answer_rate = 0
    if total_questions:
        answer_rate = round((has_answer / total_questions) * 100, 1)

    auto_score = int(submission.auto_score or 0)
    teacher_score = int(submission.teacher_score or 0)
    total_score = int(submission.total_score or (auto_score + teacher_score))

    if lang == "en":
        lines = [
            "1. Key Points and Challenges",
            f"- Question count: {total_questions} (objective {objective_count}, subjective {subjective_count})",
            f"- Topic: {exercise.title or 'This assignment'}",
        ]
        if key_points:
            lines.append(f"- Focus areas: {'; '.join(key_points[:3])}")

        lines.extend(
            [
                "",
                "2. Student Performance Summary",
                f"- Auto score: {auto_score}",
                f"- Teacher subjective score: {teacher_score}",
                f"- Total score: {total_score}",
                f"- Completion rate: {answer_rate}%",
                f"- Current status: {submission.status}",
                "",
                "3. Teaching Suggestions",
                "- Review missed questions first, then assign 3-5 targeted practice questions of similar type.",
                "- For subjective questions, emphasize step-by-step reasoning and unit/conclusion checks.",
            ]
        )
    else:
        lines = [
            "1. 重难点",
            f"- 题量：{total_questions}（客观题 {objective_count}，主观题 {subjective_count}）",
            f"- 主题：{exercise.title or '本次作业'}",
        ]
        if key_points:
            lines.append(f"- 重点内容：{'；'.join(key_points[:3])}")

        lines.extend(
            [
                "",
                "2. 学生情况总结",
                f"- 自动得分：{auto_score}",
                f"- 教师主观题得分：{teacher_score}",
                f"- 总分：{total_score}",
                f"- 作答完成率：{answer_rate}%",
                f"- 当前状态：{submission.status}",
                "",
                "3. 教学建议",
                "- 先复盘失分题，再进行同类题3-5道针对训练。",
                "- 主观题建议增加步骤表达与单位/结论检查。",
            ]
        )
    return "\n".join(lines)


def _digest_text(raw):
    text = str(raw or "")
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _review_ai_marker(exercise, submission):
    updated = submission.updated_at.strftime("%Y-%m-%d %H:%M:%S") if submission.updated_at else ""
    return "|".join(
        [
            f"u:{updated}",
            f"st:{submission.status or ''}",
            f"a:{int(submission.auto_score or 0)}",
            f"t:{int(submission.teacher_score or 0)}",
            f"ttl:{int(submission.total_score or 0)}",
            f"ac:{_digest_text(submission.answers)}",
            f"tc:{_digest_text(submission.teacher_comment)}",
            f"td:{_digest_text(submission.teacher_detail)}",
            f"ex:{_digest_text(exercise.content_json)}",
        ]
    )


@bp.route("/review", methods=["GET"])
@token_required
def list_review():
    user_id = int(getattr(g, "current_user_id", 0) or 0)
    if not user_id:
        return err("missing user", http_status=401)

    class_id = request.args.get("class_id")
    status = (request.args.get("status") or "pending_review").strip()

    pubs_q = ResourcePublish.query.filter_by(created_by=user_id, revoked=False)
    if class_id:
        try:
            class_id = int(class_id)
            pubs_q = pubs_q.filter_by(class_id=class_id)
        except ValueError:
            return err("invalid class_id", http_status=400)

    pubs = pubs_q.all()
    pub_ids = [p.id for p in pubs]
    if not pub_ids:
        return ok([])

    submissions = ExerciseSubmission.query.filter(
        ExerciseSubmission.publish_id.in_(pub_ids),
        ExerciseSubmission.status == status,
    ).all()

    student_ids = [s.student_id for s in submissions]
    students = {s.id: s for s in Student.query.filter(Student.id.in_(student_ids)).all()} if student_ids else {}

    class_ids = list({p.class_id for p in pubs})
    classes = {c.id: c for c in Classroom.query.filter(Classroom.id.in_(class_ids)).all()} if class_ids else {}
    exercises = {
        e.id: e
        for e in Exercise.query.filter(
            Exercise.id.in_([p.resource_id for p in pubs if p.resource_type == "exercise"])
        ).all()
    } if pubs else {}

    pub_map = {p.id: p for p in pubs}
    result = []
    for s in submissions:
        pub = pub_map.get(s.publish_id)
        if not pub:
            continue
        ex = exercises.get(pub.resource_id)
        student = students.get(s.student_id)
        result.append(
            {
                "submission_id": s.id,
                "publish_id": s.publish_id,
                "class_id": pub.class_id,
                "class_name": classes.get(pub.class_id).name if classes.get(pub.class_id) else "",
                "title": ex.title if ex else "",
                "auto_score": s.auto_score,
                "student_name": student.name if student else "",
                "status": s.status,
                "created_at": s.created_at.strftime("%Y-%m-%d %H:%M:%S") if s.created_at else "",
            }
        )

    return ok(result)


@bp.route("/review/<int:submission_id>", methods=["GET"])
@token_required
def review_detail(submission_id: int):
    user_id = int(getattr(g, "current_user_id", 0) or 0)
    if not user_id:
        return err("missing user", http_status=401)

    submission = ExerciseSubmission.query.get(submission_id)
    if not submission:
        return err("submission not found", http_status=404)

    pub = ResourcePublish.query.get(submission.publish_id)
    if not pub or pub.created_by != user_id:
        return err("not allowed", http_status=403)

    exercise = Exercise.query.get(pub.resource_id)
    if not exercise or not exercise.content_json:
        return err("exercise format not supported", http_status=400)

    try:
        structured = json.loads(exercise.content_json)
    except Exception:
        return err("invalid exercise format", http_status=400)

    answers = _safe_json_loads(submission.answers, {})
    teacher_detail = _safe_json_loads(submission.teacher_detail, {})

    questions = []
    for q in structured.get("questions", []):
        q2 = dict(q)
        qid = q.get("id")
        qtype = (q.get("type") or "").lower()
        q2["student_answer"] = answers.get(qid)
        q2["is_subjective"] = qtype in ("short", "essay")
        q2["teacher_score"] = (teacher_detail.get(qid) or {}).get("score") if qid else None
        questions.append(q2)

    return ok(
        {
            "submission_id": submission.id,
            "publish_id": pub.id,
            "title": exercise.title,
            "auto_score": submission.auto_score,
            "teacher_score": submission.teacher_score,
            "total_score": submission.total_score,
            "teacher_comment": submission.teacher_comment or "",
            "status": submission.status,
            "questions": questions,
        }
    )


@bp.route("/review/<int:submission_id>/ai-summary", methods=["GET"])
@token_required
def review_ai_summary(submission_id: int):
    lang = _normalize_lang(request.args.get("lang") or "zh")

    user_id = int(getattr(g, "current_user_id", 0) or 0)
    if not user_id:
        return err("missing user", http_status=401)

    submission = ExerciseSubmission.query.get(submission_id)
    if not submission:
        return err("submission not found", http_status=404)

    pub = ResourcePublish.query.get(submission.publish_id)
    if not pub or pub.created_by != user_id:
        return err("not allowed", http_status=403)

    exercise = Exercise.query.get(pub.resource_id)
    if not exercise or not exercise.content_json:
        return err("exercise format not supported", http_status=400)

    structured = _safe_json_loads(exercise.content_json, {})
    if not isinstance(structured, dict):
        return err("invalid exercise format", http_status=400)

    marker = _review_ai_marker(exercise, submission)
    cache_key = f"{submission_id}:{lang}"
    cached = _REVIEW_AI_SUMMARY_CACHE.get(cache_key)
    if cached and cached.get("marker") == marker:
        return ok(
            {
                "summary": cached.get("summary") or "",
                "source": cached.get("source") or "cache",
                "cached": True,
            }
        )

    local_summary = _build_local_review_summary(exercise, structured, submission, lang)

    try:
        if lang == "en":
            prompt = (
                "You are an elementary education assistant. Based on the assignment and student answers, "
                "write concise and actionable teacher feedback.\n"
                "Use exactly three sections:\n"
                "1) Key Points and Challenges\n"
                "2) Student Performance Summary\n"
                "3) Teaching Suggestions (max 3 items)\n"
                "Language: English. Be specific and quantitative when possible.\n\n"
                f"Assignment title: {exercise.title or ''}\n"
                f"Assignment structure (JSON): {json.dumps(structured, ensure_ascii=False)}\n"
                f"Student answers (JSON): {submission.answers or '{}'}\n"
                f"Auto score: {submission.auto_score or 0}\n"
                f"Teacher subjective score: {submission.teacher_score or 0}\n"
                f"Total score: {submission.total_score or 0}\n"
                f"Status: {submission.status or ''}\n"
            )
        else:
            prompt = (
                "你是一位小学教学教研助理。请根据以下作业与学生作答，输出简洁、可执行的教师反馈。\n"
                "输出格式固定为三部分：\n"
                "1) 本次作业重难点\n"
                "2) 学生情况总结\n"
                "3) 教学建议（3条以内）\n"
                "语言：中文，避免空话，每条尽量量化。\n\n"
                f"作业标题：{exercise.title or ''}\n"
                f"作业结构(JSON)：{json.dumps(structured, ensure_ascii=False)}\n"
                f"学生作答(JSON)：{submission.answers or '{}'}\n"
                f"自动得分：{submission.auto_score or 0}\n"
                f"教师主观题得分：{submission.teacher_score or 0}\n"
                f"总分：{submission.total_score or 0}\n"
                f"状态：{submission.status or ''}\n"
            )
        ai_text = ai_service.generate_text(prompt)
        summary = (ai_text or "").strip() or local_summary
        _REVIEW_AI_SUMMARY_CACHE[cache_key] = {"marker": marker, "summary": summary, "source": "gemini"}
        return ok({"summary": summary, "source": "gemini", "cached": False})
    except Exception:
        _REVIEW_AI_SUMMARY_CACHE[cache_key] = {"marker": marker, "summary": local_summary, "source": "fallback"}
        return ok({"summary": local_summary, "source": "fallback", "cached": False})


@bp.route("/review/history", methods=["GET"])
@token_required
def review_history():
    user_id = int(getattr(g, "current_user_id", 0) or 0)
    if not user_id:
        return err("missing user", http_status=401)

    class_id = request.args.get("class_id")
    title_kw = (request.args.get("title") or "").strip()
    student_kw = (request.args.get("student") or "").strip()

    pubs_q = ResourcePublish.query.filter_by(created_by=user_id, revoked=False)
    if class_id:
        try:
            class_id = int(class_id)
            pubs_q = pubs_q.filter_by(class_id=class_id)
        except ValueError:
            return err("invalid class_id", http_status=400)

    pubs = pubs_q.all()
    pub_ids = [p.id for p in pubs]
    if not pub_ids:
        return ok([])

    submissions = ExerciseSubmission.query.filter(
        ExerciseSubmission.publish_id.in_(pub_ids),
        ExerciseSubmission.status == "graded",
    ).order_by(ExerciseSubmission.updated_at.desc()).all()

    class_ids = list({p.class_id for p in pubs})
    classes = {c.id: c for c in Classroom.query.filter(Classroom.id.in_(class_ids)).all()} if class_ids else {}
    exercises = {
        e.id: e
        for e in Exercise.query.filter(
            Exercise.id.in_([p.resource_id for p in pubs if p.resource_type == "exercise"])
        ).all()
    } if pubs else {}
    students = {
        s.id: s for s in Student.query.filter(Student.id.in_([s.student_id for s in submissions])).all()
    } if submissions else {}

    pub_map = {p.id: p for p in pubs}
    result = []
    for s in submissions:
        pub = pub_map.get(s.publish_id)
        if not pub:
            continue
        ex = exercises.get(pub.resource_id)
        student = students.get(s.student_id)

        if title_kw and ex and title_kw not in (ex.title or ""):
            continue
        if student_kw and student and student_kw not in (student.name or ""):
            continue

        result.append(
            {
                "submission_id": s.id,
                "publish_id": s.publish_id,
                "class_id": pub.class_id,
                "class_name": classes.get(pub.class_id).name if classes.get(pub.class_id) else "",
                "title": ex.title if ex else "",
                "auto_score": s.auto_score,
                "teacher_score": s.teacher_score,
                "total_score": s.total_score,
                "student_name": student.name if student else "",
                "teacher_comment": s.teacher_comment or "",
                "status": s.status,
                "created_at": s.updated_at.strftime("%Y-%m-%d %H:%M:%S") if s.updated_at else "",
            }
        )

    return ok(result)


@bp.route("/review/<int:submission_id>/score", methods=["POST"])
@token_required
def review_score(submission_id: int):
    user_id = int(getattr(g, "current_user_id", 0) or 0)
    if not user_id:
        return err("missing user", http_status=401)

    submission = ExerciseSubmission.query.get(submission_id)
    if not submission:
        return err("submission not found", http_status=404)

    pub = ResourcePublish.query.get(submission.publish_id)
    if not pub or pub.created_by != user_id:
        return err("not allowed", http_status=403)

    data = request.get_json(silent=True) or {}
    scores = data.get("scores") or {}
    teacher_comment = data.get("teacher_comment") or ""

    exercise = Exercise.query.get(pub.resource_id)
    if not exercise or not exercise.content_json:
        return err("exercise format not supported", http_status=400)

    try:
        structured = json.loads(exercise.content_json)
    except Exception:
        return err("invalid exercise format", http_status=400)

    max_scores = {}
    subjective_ids = set()
    for q in structured.get("questions", []):
        qid = q.get("id")
        if not qid:
            continue
        qtype = (q.get("type") or "").lower()
        if qtype in ("short", "essay"):
            subjective_ids.add(qid)
            try:
                max_scores[qid] = int(q.get("score") or 0)
            except Exception:
                max_scores[qid] = 0

    teacher_detail = {}
    teacher_score = 0
    for qid, raw_score in scores.items():
        if qid not in subjective_ids:
            continue
        try:
            score = int(raw_score)
        except Exception:
            return err("invalid teacher_score", http_status=400)
        max_s = max_scores.get(qid, 0)
        if score < 0 or score > max_s:
            return err("invalid teacher_score", http_status=400)
        teacher_detail[qid] = {"score": score}
        teacher_score += score

    submission.teacher_score = teacher_score
    submission.teacher_detail = json.dumps(teacher_detail, ensure_ascii=False)
    submission.teacher_comment = teacher_comment
    submission.total_score = (submission.auto_score or 0) + teacher_score
    submission.status = "graded"
    db.session.commit()

    assignment = ResourceAssignment.query.filter_by(
        publish_id=submission.publish_id,
        student_id=submission.student_id,
    ).first()
    if assignment:
        assignment.score = submission.total_score
        assignment.status = "completed"
        db.session.commit()

    return ok(submission.to_dict())
