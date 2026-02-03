# app\api\auth\routes.py
from flask import Blueprint, request
from app.extensions import db
from app.models.user import User
from app.utils.response import ok, err

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

@bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "").strip()

    if not name or not email or not password:
        return err("missing fields", http_status=400)

    if User.query.filter_by(email=email).first():
        return err("email already exists", http_status=409)

    user = User(name=name, email=email)
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    return ok({"user": {"id": user.id, "name": user.name, "email": user.email}}, "register success")

@bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "").strip()

    if not email or not password:
        return err("missing fields", http_status=400)

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return err("invalid credentials", http_status=401)

    return ok({"user": {"id": user.id, "name": user.name, "email": user.email}}, "login success")
