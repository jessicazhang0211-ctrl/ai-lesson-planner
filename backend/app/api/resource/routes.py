from flask import Blueprint, request, g
from app.utils.response import ok, err
from app.utils.auth import token_required
from app.extensions import db
from app.models.resource_publish import ResourcePublish
from app.models.resource_assignment import ResourceAssignment
from app.models.lesson import Lesson
from app.models.exercise import Exercise
from app.models.classroom import Classroom
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

    pubs = (ResourcePublish.query
        .filter_by(created_by=user_id, resource_type=resource_type, resource_id=resource_id, revoked=False)
        .all())

    pub_ids = [p.id for p in pubs]
    if not pub_ids:
        return ok({"overall": {"assigned": 0, "completed": 0, "rate": 0}, "classes": []})

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

    return ok({
        "overall": {"assigned": total_assigned, "completed": total_completed, "rate": rate},
        "classes": class_list
    })
