from .shared import *
from .shared import _load_ids
from flask import current_app


def _format_dt(value):
    if not value:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value)

@bp.route("/ping", methods=["GET"])
def ping():
    return ok({"status": "ok"})


@bp.route("/assignments", methods=["GET"])
@token_required
def list_assignments():
    user_id = int(getattr(g, "current_user_id", 0) or 0)
    try:
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

        cls = Classroom.query.get(profile.class_id)
        class_name = cls.name if cls else ""

        result = []
        for p in pubs:
            ids = _load_ids(p.student_ids)
            if profile.student_id not in ids:
                continue
            assignment = assignment_map.get(p.id)
            lesson_obj = lessons.get(p.resource_id) if p.resource_type == "lesson" else None
            exercise_obj = exercises.get(p.resource_id) if p.resource_type == "exercise" else None
            title = ""
            if lesson_obj:
                title = lesson_obj.title or ""
            elif exercise_obj:
                title = exercise_obj.title or ""
            result.append({
                "publish_id": p.id,
                "resource_type": p.resource_type,
                "resource_id": p.resource_id,
                "title": title or "",
                "class_id": profile.class_id,
                "class_name": class_name,
                "created_at": _format_dt(p.created_at),
                "status": assignment.status if assignment else "assigned"
            })

        return ok(result)
    except Exception as ex:
        current_app.logger.exception("list_assignments failed, user_id=%s", user_id)
        return err(f"list_assignments internal error: {ex}", http_status=500)


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
    if submission:
        submission_status = submission.status or ""
        auto_score = submission.auto_score
        teacher_score = submission.teacher_score
        total_score = submission.total_score
        if submission.answers:
            try:
                draft_answers = json.loads(submission.answers)
            except Exception:
                draft_answers = {}
        if submission.auto_result:
            try:
                auto_result = json.loads(submission.auto_result)
            except Exception:
                auto_result = {}
        if submission_status == "pending_review" and (teacher_score is not None or total_score is not None):
            submission_status = "graded"

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


