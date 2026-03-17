# app/api/user/routes.py
from flask import Blueprint, request
from app.extensions import db
from app.models.user import User
from app.utils.response import ok, err
from app.utils.auth import validate_password_strength

bp = Blueprint("user", __name__, url_prefix="/api/user")

def get_uid() -> int | None:
    uid = (request.headers.get("X-User-Id") or "").strip()
    if not uid:
        return None
    try:
        return int(uid)
    except ValueError:
        return None

@bp.route("/me", methods=["GET", "OPTIONS"])
def get_me():
    if request.method == "OPTIONS":
        return "", 204

    uid = get_uid()
    if not uid:
        return err("missing X-User-Id", http_status=401)

    user = User.query.get(uid)
    if not user:
        return err("user not found", http_status=404)

    return ok({
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "nickname": user.nickname,
        "gender": user.gender,
        "bio": user.bio,
        "phone": user.phone,
        "school": user.school,
        "major": user.major,
        "job_title": user.job_title,
        "avatar_url": user.avatar_url
    })

@bp.route("/me", methods=["PATCH", "OPTIONS"])
def update_me():
    if request.method == "OPTIONS":
        return "", 204

    uid = get_uid()
    if not uid:
        return err("missing X-User-Id", http_status=401)

    user = User.query.get(uid)
    if not user:
        return err("user not found", http_status=404)

    payload = request.get_json(silent=True) or {}

    allowed = {
        "nickname", "gender", "bio", "phone",
        "school", "major", "job_title", "avatar_url"
    }

    updates = {k: payload.get(k) for k in payload if k in allowed}
    if not updates:
        return err("no valid fields", http_status=400)

    if "gender" in updates:
        g = (updates["gender"] or "").strip()
        if g and g not in ["male", "female", "男", "女"]:
            return err("invalid gender", http_status=400)

    for k, v in updates.items():
        setattr(user, k, v)

    db.session.commit()

    return ok({
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "nickname": user.nickname,
            "gender": user.gender,
            "bio": user.bio,
            "phone": user.phone,
            "school": user.school,
            "major": user.major,
            "job_title": user.job_title,
            "avatar_url": user.avatar_url
        }
    }, "updated")

@bp.route("/change-password", methods=["POST", "OPTIONS"])
def change_password():
    if request.method == "OPTIONS":
        return "", 204

    uid = get_uid()
    if not uid:
        return err("missing X-User-Id", http_status=401)

    user = User.query.get(uid)
    if not user:
        return err("user not found", http_status=404)

    data = request.get_json(silent=True) or {}
    current_password = (data.get("current_password") or "").strip()
    new_password = (data.get("new_password") or "").strip()

    if not current_password or not new_password:
        return err("missing fields", http_status=400)

    strong, msg = validate_password_strength(new_password)
    if not strong:
        return err(msg, http_status=400)

    if not user.check_password(current_password):
        return err("current password incorrect", http_status=400)

    user.set_password(new_password)
    db.session.commit()

    return ok("password changed")
