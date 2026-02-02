# app/api/user/routes.py
from flask import Blueprint, request, jsonify
from app.db import get_db

bp = Blueprint("user", __name__, url_prefix="/api/user")

@bp.route("/me", methods=["GET"])
def get_me():
    user_id = request.headers.get("X-User-Id")
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE id=%s", (user_id,))
    user = cur.fetchone()
    return jsonify({"code": 0, "data": user})


@bp.route("/me", methods=["PATCH"])
def update_me():
    user_id = request.headers.get("X-User-Id")
    data = request.json or {}

    allowed = {
        "nickname", "gender", "bio",
        "phone", "school", "major", "job_title"
    }
    fields = {k: v for k, v in data.items() if k in allowed}

    if not fields:
        return jsonify({"code": 1, "message": "no valid fields"}), 400

    sets = ", ".join(f"{k}=%s" for k in fields)
    values = list(fields.values()) + [user_id]

    db = get_db()
    cur = db.cursor()
    cur.execute(f"UPDATE users SET {sets} WHERE id=%s", values)
    db.commit()

    cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE id=%s", (user_id,))
    user = cur.fetchone()

    return jsonify({"code": 0, "data": {"user": user}})
