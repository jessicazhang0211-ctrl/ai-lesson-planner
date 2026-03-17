import json

from flask import g, request

from app.extensions import db
from app.models.classroom import Classroom, Student
from app.models.exercise import Exercise
from app.models.exercise_submission import ExerciseSubmission
from app.models.resource_assignment import ResourceAssignment
from app.models.resource_publish import ResourcePublish
from app.utils.auth import token_required
from app.utils.response import err, ok

from .blueprint import bp


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

    answers = {}
    try:
        answers = json.loads(submission.answers or "{}")
    except Exception:
        answers = {}

    teacher_detail = {}
    try:
        teacher_detail = json.loads(submission.teacher_detail or "{}")
    except Exception:
        teacher_detail = {}

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
