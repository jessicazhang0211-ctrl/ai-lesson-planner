from flask import Blueprint, request, g
from app.utils.response import ok, err
from app.utils.auth import token_required
from app.extensions import db
from app.models.resource_publish import ResourcePublish
from app.models.lesson import Lesson
from app.models.exercise import Exercise
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
        created_by=created_by,
        created_at=datetime.datetime.now()
    )

    db.session.add(record)
    db.session.commit()
    return ok(record.to_dict())


@bp.route("/publish", methods=["GET"])
@token_required
def list_published():
    class_id = request.args.get("class_id")
    if not class_id:
        return err("class_id required", http_status=400)

    try:
        class_id = int(class_id)
    except ValueError:
        return err("invalid class_id", http_status=400)

    user_id = int(getattr(g, "current_user_id", 0) or 0)
    if not user_id:
        return err("missing user", http_status=401)

    records = (ResourcePublish.query
        .filter_by(created_by=user_id, class_id=class_id)
        .order_by(ResourcePublish.created_at.desc())
        .limit(10)
        .all())

    lesson_ids = [r.resource_id for r in records if r.resource_type == "lesson"]
    exercise_ids = [r.resource_id for r in records if r.resource_type == "exercise"]

    lessons = {l.id: l for l in Lesson.query.filter(Lesson.id.in_(lesson_ids)).all()} if lesson_ids else {}
    exercises = {e.id: e for e in Exercise.query.filter(Exercise.id.in_(exercise_ids)).all()} if exercise_ids else {}

    result = []
    for r in records:
        data = r.to_dict()
        if r.resource_type == "lesson":
            data["title"] = lessons.get(r.resource_id).title if lessons.get(r.resource_id) else ""
        else:
            data["title"] = exercises.get(r.resource_id).title if exercises.get(r.resource_id) else ""
        result.append(data)

    return ok(result)
