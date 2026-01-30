from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models.user import User

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

@bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "").strip()

    if not name or not email or not password:
        return jsonify({"code": 1, "message": "missing fields"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"code": 1, "message": "email already exists"}), 409

    user = User(name=name, email=email)
    user.set_password(password)

    db.session.add(user)
    db.session.commit()
    print("✅ inserted user id =", user.id, "email =", user.email)


    return jsonify({
        "code": 0,
        "message": "register success",
        "data": {"user": {"id": user.id, "name": user.name, "email": user.email}}
    })


@bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "").strip()

    if not email or not password:
        return jsonify({"code": 1, "message": "missing fields"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"code": 1, "message": "invalid credentials"}), 401

    return jsonify({
        "code": 0,
        "message": "login success",
        "data": {"user": {"id": user.id, "name": user.name, "email": user.email}}
    })
