# app\api\auth\routes.py
from flask import Blueprint, request
from app.extensions import db
from app.models.user import User
from app.models.classroom import Student
from app.models.student_profile import StudentProfile
from app.utils.response import ok, err
from app.utils.auth import generate_token
from app.utils.auth import validate_password_strength

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

@bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "").strip()
    role = (data.get("role") or "teacher").strip()

    if role == "student":
        return err("student self-registration disabled", http_status=403)

    if not name or not email or not password:
        return err("missing fields", http_status=400)

    strong, msg = validate_password_strength(password)
    if not strong:
        return err(msg, http_status=400)

    if User.query.filter_by(email=email).first():
        return err("email already exists", http_status=409)

    user = User(name=name, email=email)
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    return ok({"user": {"id": user.id, "name": user.name, "email": user.email, "role": "teacher"}}, "register success")

@bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    stu_id = (data.get("stu_id") or "").strip()
    password = (data.get("password") or "").strip()

    if not password:
        return err("missing fields", http_status=400)

    if not email and not stu_id:
        return err("missing fields", http_status=400)

    user = None
    profile = None
    if email:
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            return err("invalid credentials", http_status=401)
    else:
        students = Student.query.filter_by(stu_id=stu_id).all()
        matched = []
        for s in students:
            sp = StudentProfile.query.filter_by(student_id=s.id).first()
            if not sp:
                continue
            u = User.query.get(sp.user_id)
            if not u or not u.check_password(password):
                continue
            matched.append((u, sp))
        if not matched:
            return err("invalid credentials", http_status=401)
        if len(matched) > 1:
            return err("duplicate student id, please contact teacher", http_status=409)
        user, profile = matched[0]

    token = generate_token(user.id)
    if not profile:
        profile = StudentProfile.query.filter_by(user_id=user.id).first()
    payload = {"id": user.id, "name": user.name, "email": user.email}
    must_change_password = False
    if profile:
        payload["role"] = "student"
        payload["class_id"] = profile.class_id
        payload["student_id"] = profile.student_id
        must_change_password = user.check_password("123456")
    else:
        payload["role"] = "teacher"
    return ok({"user": payload, "token": token, "must_change_password": must_change_password}, "login success")
