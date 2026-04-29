import datetime
import json

from flask import g, request

from app.extensions import db
from app.models.classroom import Classroom
from app.models.exercise import Exercise
from app.models.lesson import Lesson
from app.models.resource_assignment import ResourceAssignment
from app.models.resource_publish import ResourcePublish
from app.utils.auth import token_required
from app.utils.response import err, ok

from .blueprint import bp


def _extract_lesson_meta(lesson: Lesson) -> dict:
    if not lesson or not isinstance(lesson.description, str):
        return {}
    desc = lesson.description or ""
    if not desc.startswith("__META__"):
        return {}
    try:
        meta_str, _ = desc.split("__\n", 1)
        meta = json.loads(meta_str.replace("__META__", ""))
        return meta if isinstance(meta, dict) else {}
    except Exception:
        return {}


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

    if resource_type == "lesson":
        lesson = Lesson.query.get(int(resource_id))
        if not lesson or int(lesson.created_by) != created_by:
            return err("lesson not found", http_status=404)

        lesson_meta = _extract_lesson_meta(lesson)
        review_required = bool(lesson_meta.get("teacher_review_required"))
        review_approved = bool(lesson_meta.get("teacher_review_approved"))
        need_review = bool(lesson_meta.get("need_review") or lesson_meta.get("status") == "need_review")

        if review_required and not review_approved:
            return err("lesson requires teacher review approval before publish", http_status=409)
        if need_review and not review_approved:
            return err("lesson is marked need_review; please review/save before publish", http_status=409)
    else:
        exercise = Exercise.query.get(int(resource_id))
        if not exercise or int(exercise.created_by) != created_by:
            return err("exercise not found", http_status=404)

    record = ResourcePublish(
        resource_type=resource_type,
        resource_id=int(resource_id),
        class_id=int(class_id),
        student_ids=json.dumps(student_ids, ensure_ascii=False),
        accuracy_rule=json.dumps(accuracy_rule, ensure_ascii=False),
        mode=mode,
        revoked=False,
        created_by=created_by,
        created_at=datetime.datetime.now(),
    )

    db.session.add(record)
    db.session.commit()

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
