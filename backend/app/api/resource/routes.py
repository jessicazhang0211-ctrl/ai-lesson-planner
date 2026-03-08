from flask import Blueprint, request, g
from app.utils.response import ok, err
from app.utils.auth import token_required
from app.extensions import db
from app.models.resource_publish import ResourcePublish
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
