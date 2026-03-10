# app\api\auth\routes.py
from flask import Blueprint, request
from app.extensions import db
from app.models.user import User
from app.models.classroom import Classroom, Student
from app.models.student_profile import StudentProfile
from app.utils.response import ok, err
from app.utils.auth import generate_token

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

@bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "").strip()
    role = (data.get("role") or "teacher").strip()
    class_id = data.get("class_id")

    if not name or not email or not password:
        return err("missing fields", http_status=400)

    if User.query.filter_by(email=email).first():
        return err("email already exists", http_status=409)

    if role == "student":
        if not class_id:
            return err("class_id required", http_status=400)
        cls = Classroom.query.get(int(class_id))
        if not cls or cls.status != "active":
            return err("class not found", http_status=404)

    user = User(name=name, email=email)
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    if role == "student":
        student = Student(
            name=name,
            stu_id=data.get("stu_id") or "",
            status="joined",
            parent_phone=data.get("parent_phone") or "",
            class_id=cls.id
        )
        db.session.add(student)
        db.session.commit()

        profile = StudentProfile(user_id=user.id, class_id=cls.id, student_id=student.id)
        db.session.add(profile)
        db.session.commit()

        return ok({"user": {"id": user.id, "name": user.name, "email": user.email, "role": "student", "class_id": cls.id}}, "register success")

    return ok({"user": {"id": user.id, "name": user.name, "email": user.email, "role": "teacher"}}, "register success")

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

    token = generate_token(user.id)
    profile = StudentProfile.query.filter_by(user_id=user.id).first()
    payload = {"id": user.id, "name": user.name, "email": user.email}
    if profile:
        payload["role"] = "student"
        payload["class_id"] = profile.class_id
        payload["student_id"] = profile.student_id
    else:
        payload["role"] = "teacher"
    return ok({"user": payload, "token": token}, "login success")
