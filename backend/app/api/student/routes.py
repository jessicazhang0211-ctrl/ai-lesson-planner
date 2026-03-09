from flask import Blueprint, g
from app.utils.auth import token_required
from app.utils.response import ok, err
from app.models.student_profile import StudentProfile
from app.models.resource_publish import ResourcePublish
from app.models.resource_assignment import ResourceAssignment
from app.models.lesson import Lesson
from app.models.exercise import Exercise
import json

bp = Blueprint("student", __name__, url_prefix="/api/student")


def _load_ids(raw):
    try:
        return json.loads(raw) if raw else []
    except Exception:
        return []


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
