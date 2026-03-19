from .shared import *
from .shared import _load_ids, _grade_objective

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


@bp.route("/review/<int:publish_id>", methods=["GET"])
@token_required
def review_exercise(publish_id: int):
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

    assignment = ResourceAssignment.query.filter_by(publish_id=pub.id, student_id=profile.student_id).first()
    if not assignment or assignment.status != "completed":
        return err("assignment not completed", http_status=400)

    submission = ExerciseSubmission.query.filter_by(publish_id=pub.id, student_id=profile.student_id).first()
    if not submission:
        return err("submission not found", http_status=404)

    exercise = Exercise.query.get(pub.resource_id)
    if not exercise or not exercise.content_json:
        return err("exercise format not supported", http_status=400)

    try:
        structured = json.loads(exercise.content_json)
    except Exception:
        return err("invalid exercise format", http_status=400)

    try:
        answers = json.loads(submission.answers or "{}")
    except Exception:
        answers = {}

    try:
        auto_result = json.loads(submission.auto_result or "{}")
    except Exception:
        auto_result = {}

    try:
        teacher_detail = json.loads(submission.teacher_detail or "{}")
    except Exception:
        teacher_detail = {}

    questions = []
    for q in structured.get("questions", []):
        qid = q.get("id")
        q2 = dict(q)
        q2["student_answer"] = answers.get(qid)
        q2["result"] = auto_result.get(qid)
        q2["teacher_score"] = (teacher_detail.get(qid) or {}).get("score") if qid else None
        questions.append(q2)

    return ok({
        "publish_id": pub.id,
        "title": exercise.title,
        "questions": questions,
        "auto_score": submission.auto_score,
        "teacher_score": submission.teacher_score,
        "total_score": submission.total_score,
        "status": "graded" if (submission.teacher_score is not None or submission.teacher_detail) else submission.status
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
    max_score_map = {}
    for ex in exercises.values():
        if not ex or not ex.content_json:
            continue
        try:
            structured = json.loads(ex.content_json)
        except Exception:
            continue
        total = 0
        for q in structured.get("questions", []):
            try:
                total += int(q.get("score") or 0)
            except Exception:
                continue
        max_score_map[ex.id] = total

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
            "max_score": max_score_map.get(p.resource_id),
            "completed_at": a.completed_at.strftime("%Y-%m-%d %H:%M:%S") if a and a.completed_at else "",
            "published_at": p.created_at.strftime("%Y-%m-%d %H:%M:%S") if p.created_at else ""
        })

    return ok(result)



