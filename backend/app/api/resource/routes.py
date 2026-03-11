from flask import Blueprint, request, g
from app.utils.response import ok, err
from app.utils.auth import token_required
from app.extensions import db
from app.models.resource_publish import ResourcePublish
from app.models.resource_assignment import ResourceAssignment
from app.models.exercise_submission import ExerciseSubmission
from app.models.lesson import Lesson
from app.models.exercise import Exercise
from app.models.classroom import Classroom, Student
import json
import datetime

bp = Blueprint("resource", __name__, url_prefix="/api/resource")


@bp.route("/publish", methods=["POST", "OPTIONS"])
@token_required
def publish_resource():
    if request.method == "OPTIONS":
        return "", 204

    data = request.get_json(silent=True) or {}
    resource_type = (data.get("resource_type") or "").strip()
    resource_id = data.get("resource_id")
    class_id = data.get("class_id")
    student_ids = data.get("student_ids") or []
    accuracy_rule = data.get("accuracy_rule") or {}
    mode = data.get("mode") or ""

    if resource_type not in ("lesson", "exercise"):
        return err("invalid resource_type", http_status=400)
    if not resource_id or not class_id:
        return err("resource_id and class_id required", http_status=400)
    if not isinstance(student_ids, list) or not student_ids:
        return err("student_ids required", http_status=400)

    created_by = int(getattr(g, "current_user_id", 0) or 0)
    if not created_by:
        return err("missing user", http_status=401)

    record = ResourcePublish(
        resource_type=resource_type,
        resource_id=int(resource_id),
        class_id=int(class_id),
        student_ids=json.dumps(student_ids, ensure_ascii=False),
        accuracy_rule=json.dumps(accuracy_rule, ensure_ascii=False),
        mode=mode,
        revoked=False,
        created_by=created_by,
        created_at=datetime.datetime.now()
    )

    db.session.add(record)
    db.session.commit()

    # create assignment rows for tracking completion
    assignments = []
    for sid in student_ids:
        try:
            assignments.append(ResourceAssignment(publish_id=record.id, student_id=int(sid)))
        except Exception:
            continue
    if assignments:
        db.session.add_all(assignments)
        db.session.commit()
    return ok(record.to_dict())


@bp.route("/publish", methods=["GET"])
@token_required
def list_published():
    class_id = request.args.get("class_id")
    user_id = int(getattr(g, "current_user_id", 0) or 0)
    if not user_id:
        return err("missing user", http_status=401)

    q = ResourcePublish.query.filter_by(created_by=user_id, revoked=False)
    if class_id:
        try:
            class_id = int(class_id)
        except ValueError:
            return err("invalid class_id", http_status=400)
        q = q.filter_by(class_id=class_id)

    records = q.order_by(ResourcePublish.created_at.desc()).limit(10 if class_id else 50).all()

    lesson_ids = [r.resource_id for r in records if r.resource_type == "lesson"]
    exercise_ids = [r.resource_id for r in records if r.resource_type == "exercise"]
    class_ids = [r.class_id for r in records]

    lessons = {l.id: l for l in Lesson.query.filter(Lesson.id.in_(lesson_ids)).all()} if lesson_ids else {}
    exercises = {e.id: e for e in Exercise.query.filter(Exercise.id.in_(exercise_ids)).all()} if exercise_ids else {}
    classes = {c.id: c for c in Classroom.query.filter(Classroom.id.in_(class_ids)).all()} if class_ids else {}

    result = []
    for r in records:
        data = r.to_dict()
        if r.resource_type == "lesson":
            data["title"] = lessons.get(r.resource_id).title if lessons.get(r.resource_id) else ""
        else:
            data["title"] = exercises.get(r.resource_id).title if exercises.get(r.resource_id) else ""
        data["class_name"] = classes.get(r.class_id).name if classes.get(r.class_id) else ""
        result.append(data)

    return ok(result)


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

    submissions = ExerciseSubmission.query.filter(ExerciseSubmission.publish_id.in_(pub_ids), ExerciseSubmission.status == status).all()

    student_ids = [s.student_id for s in submissions]
    students = {s.id: s for s in Student.query.filter(Student.id.in_(student_ids)).all()} if student_ids else {}

    class_ids = list({p.class_id for p in pubs})
    classes = {c.id: c for c in Classroom.query.filter(Classroom.id.in_(class_ids)).all()} if class_ids else {}
    exercises = {e.id: e for e in Exercise.query.filter(Exercise.id.in_([p.resource_id for p in pubs if p.resource_type == "exercise"])) .all()} if pubs else {}

    pub_map = {p.id: p for p in pubs}
    result = []
    for s in submissions:
        pub = pub_map.get(s.publish_id)
        if not pub:
            continue
        ex = exercises.get(pub.resource_id)
        student = students.get(s.student_id)
        result.append({
            "submission_id": s.id,
            "publish_id": s.publish_id,
            "class_id": pub.class_id,
            "class_name": classes.get(pub.class_id).name if classes.get(pub.class_id) else "",
            "title": ex.title if ex else "",
            "auto_score": s.auto_score,
            "student_name": student.name if student else "",
            "status": s.status,
            "created_at": s.created_at.strftime("%Y-%m-%d %H:%M:%S") if s.created_at else ""
        })

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

    return ok({
        "submission_id": submission.id,
        "publish_id": pub.id,
        "title": exercise.title,
        "auto_score": submission.auto_score,
        "teacher_score": submission.teacher_score,
        "total_score": submission.total_score,
        "teacher_comment": submission.teacher_comment or "",
        "status": submission.status,
        "questions": questions
    })


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
        ExerciseSubmission.status == "graded"
    ).order_by(ExerciseSubmission.updated_at.desc()).all()

    class_ids = list({p.class_id for p in pubs})
    classes = {c.id: c for c in Classroom.query.filter(Classroom.id.in_(class_ids)).all()} if class_ids else {}
    exercises = {e.id: e for e in Exercise.query.filter(Exercise.id.in_([p.resource_id for p in pubs if p.resource_type == "exercise"])) .all()} if pubs else {}
    students = {s.id: s for s in Student.query.filter(Student.id.in_([s.student_id for s in submissions])).all()} if submissions else {}

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

        result.append({
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
            "created_at": s.updated_at.strftime("%Y-%m-%d %H:%M:%S") if s.updated_at else ""
        })

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
            s = int(raw_score)
        except Exception:
            return err("invalid teacher_score", http_status=400)
        max_s = max_scores.get(qid, 0)
        if s < 0 or s > max_s:
            return err("invalid teacher_score", http_status=400)
        teacher_detail[qid] = {"score": s}
        teacher_score += s

    submission.teacher_score = teacher_score
    submission.teacher_detail = json.dumps(teacher_detail, ensure_ascii=False)
    submission.teacher_comment = teacher_comment
    submission.total_score = (submission.auto_score or 0) + teacher_score
    submission.status = "graded"
    db.session.commit()

    assignment = ResourceAssignment.query.filter_by(publish_id=submission.publish_id, student_id=submission.student_id).first()
    if assignment:
        assignment.score = submission.total_score
        assignment.status = "completed"
        db.session.commit()

    return ok(submission.to_dict())


@bp.route("/publish/<int:pub_id>/revoke", methods=["POST"])
@token_required
def revoke_published(pub_id: int):
    user_id = int(getattr(g, "current_user_id", 0) or 0)
    if not user_id:
        return err("missing user", http_status=401)

    record = ResourcePublish.query.get(pub_id)
    if not record or record.created_by != user_id:
        return err("record not found", http_status=404)

    record.revoked = True
    record.revoked_at = datetime.datetime.now()
    db.session.commit()
    return ok(record.to_dict())


@bp.route("/resource/<string:resource_type>/<int:resource_id>/stats", methods=["GET"])
@token_required
def resource_stats(resource_type: str, resource_id: int):
    if resource_type not in ("lesson", "exercise"):
        return err("invalid resource_type", http_status=400)

    user_id = int(getattr(g, "current_user_id", 0) or 0)
    if not user_id:
        return err("missing user", http_status=401)

    class_id = request.args.get("class_id")
    pubs_q = (ResourcePublish.query
        .filter_by(created_by=user_id, resource_type=resource_type, resource_id=resource_id, revoked=False))
    if class_id:
        try:
            class_id = int(class_id)
            pubs_q = pubs_q.filter_by(class_id=class_id)
        except ValueError:
            return err("invalid class_id", http_status=400)

    pubs = pubs_q.all()

    pub_ids = [p.id for p in pubs]
    if not pub_ids:
        return ok({"overall": {"assigned": 0, "completed": 0, "rate": 0}, "classes": [], "questions": [], "trend": []})

    assignments = ResourceAssignment.query.filter(ResourceAssignment.publish_id.in_(pub_ids)).all()

    class_map = {}
    pub_to_class = {}
    for p in pubs:
        pub_to_class[p.id] = p.class_id
        if p.class_id not in class_map:
            class_map[p.class_id] = {"assigned": 0, "completed": 0, "last_published_at": p.created_at}
        if p.created_at and p.created_at > class_map[p.class_id]["last_published_at"]:
            class_map[p.class_id]["last_published_at"] = p.created_at

    for a in assignments:
        class_id = pub_to_class.get(a.publish_id)
        if not class_id:
            continue
        bucket = class_map.get(class_id)
        if not bucket:
            continue
        bucket["assigned"] += 1
        if a.status == "completed":
            bucket["completed"] += 1

    total_assigned = sum(v["assigned"] for v in class_map.values())
    total_completed = sum(v["completed"] for v in class_map.values())
    rate = int(round((total_completed / total_assigned) * 100)) if total_assigned else 0

    class_ids = list(class_map.keys())
    classes = {c.id: c for c in Classroom.query.filter(Classroom.id.in_(class_ids)).all()} if class_ids else {}

    class_list = []
    for cid, v in class_map.items():
        assigned = v["assigned"]
        completed = v["completed"]
        class_list.append({
            "class_id": cid,
            "class_name": classes.get(cid).name if classes.get(cid) else "",
            "assigned": assigned,
            "completed": completed,
            "rate": int(round((completed / assigned) * 100)) if assigned else 0,
            "last_published_at": v["last_published_at"].strftime("%Y-%m-%d %H:%M:%S") if v["last_published_at"] else ""
        })

    # exercise question stats
    questions_stats = []
    trend = []
    if resource_type == "exercise":
        exercise = Exercise.query.get(resource_id)
        if exercise and exercise.content_json:
            try:
                structured = json.loads(exercise.content_json)
            except Exception:
                structured = {}
            questions = structured.get("questions", [])

            submissions = (ExerciseSubmission.query
                .filter(ExerciseSubmission.publish_id.in_(pub_ids), ExerciseSubmission.status == "graded")
                .order_by(ExerciseSubmission.updated_at.desc())
                .all())

            # trend: last 10 graded submissions
            for s in list(reversed(submissions[:10])):
                dt = s.updated_at or s.created_at
                label = dt.strftime("%m-%d") if dt else ""
                trend.append({"label": label, "score": s.total_score})

            # build per-question stats
            totals = {}
            wrongs = {}
            counts = {}
            max_scores = {}
            qtypes = {}
            stems = {}
            analyses = {}

            for q in questions:
                qid = q.get("id")
                if not qid:
                    continue
                try:
                    max_scores[qid] = int(q.get("score") or 0)
                except Exception:
                    max_scores[qid] = 0
                qtypes[qid] = q.get("type") or ""
                stems[qid] = q.get("stem") or ""
                analyses[qid] = q.get("analysis") or ""
                totals[qid] = 0
                wrongs[qid] = 0
                counts[qid] = 0

            for s in submissions:
                try:
                    auto_result = json.loads(s.auto_result or "{}")
                except Exception:
                    auto_result = {}
                try:
                    teacher_detail = json.loads(s.teacher_detail or "{}")
                except Exception:
                    teacher_detail = {}

                for qid in counts.keys():
                    qtype = (qtypes.get(qid) or "").lower()
                    max_s = max_scores.get(qid, 0)
                    score = None
                    if qtype in ("short", "essay"):
                        score = (teacher_detail.get(qid) or {}).get("score")
                        if score is None:
                            continue
                        wrong = score < max_s
                    else:
                        result = auto_result.get(qid)
                        if result is None:
                            continue
                        score = max_s if result == "correct" else 0
                        wrong = result == "wrong"
                    totals[qid] += score
                    counts[qid] += 1
                    if wrong:
                        wrongs[qid] += 1

            for qid in counts.keys():
                if counts[qid] == 0:
                    avg_score = None
                else:
                    avg_score = round(totals[qid] / counts[qid], 2)
                questions_stats.append({
                    "id": qid,
                    "stem": stems.get(qid, ""),
                    "type": qtypes.get(qid, ""),
                    "analysis": analyses.get(qid, ""),
                    "max_score": max_scores.get(qid, 0),
                    "avg_score": avg_score,
                    "wrong_count": wrongs.get(qid, 0),
                    "answer_count": counts.get(qid, 0)
                })

    return ok({
        "overall": {"assigned": total_assigned, "completed": total_completed, "rate": rate},
        "classes": class_list,
        "questions": questions_stats,
        "trend": trend
    })
