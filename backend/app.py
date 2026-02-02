from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# ✅ CORS：允许前端 5500 + 允许 X-User-Id（解决预检失败）
CORS(
    app,
    resources={r"/api/*": {"origins": ["http://127.0.0.1:5500", "http://localhost:5500"]}},
    allow_headers=["Content-Type", "X-User-Id"],
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
)

# ====== 改成你的 MySQL 配置 ======
DB_USER = "root"
DB_PASSWORD = "123456"
DB_HOST = "127.0.0.1"
DB_PORT = "3306"
DB_NAME = "ai_lesson_planner"

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    "?charset=utf8mb4"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    # login fields
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # profile/work fields (for settings page)
    nickname = db.Column(db.String(64), nullable=True)
    gender = db.Column(db.String(16), nullable=True)       # 建议存 male/female，前端翻译显示
    bio = db.Column(db.String(500), nullable=True)
    phone = db.Column(db.String(32), nullable=True)

    school = db.Column(db.String(128), nullable=True)
    major = db.Column(db.String(128), nullable=True)
    job_title = db.Column(db.String(128), nullable=True)

    avatar_url = db.Column(db.String(255), nullable=True)

def ok(data=None, message="ok"):
    return jsonify({"code": 0, "message": message, "data": data})

def fail(message="error", status=400):
    return jsonify({"code": 1, "message": message, "data": None}), status

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

# ================= Auth =================
@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "").strip()

    if not name or not email or not password:
        return fail("missing fields", 400)

    if User.query.filter_by(email=email).first():
        return fail("email already exists", 409)

    user = User(
        name=name,
        email=email,
        password_hash=generate_password_hash(password)
    )
    db.session.add(user)
    db.session.commit()

    return ok({"user": {"id": user.id, "name": user.name, "email": user.email}}, "register success")

@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "").strip()

    if not email or not password:
        return fail("missing fields", 400)

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return fail("invalid credentials", 401)

    return ok({"user": {"id": user.id, "name": user.name, "email": user.email}}, "login success")

# ================= User: /api/user/me =================
def get_uid():
    uid = (request.headers.get("X-User-Id") or "").strip()
    if not uid:
        return None
    # uid 应该是 int
    try:
        return int(uid)
    except ValueError:
        return None

@app.route("/api/user/me", methods=["GET", "OPTIONS"])
def get_me():
    # ✅ 预检兜底
    if request.method == "OPTIONS":
        return ("", 204)

    uid = get_uid()
    if not uid:
        return fail("missing X-User-Id", 401)

    user = User.query.get(uid)
    if not user:
        return fail("user not found", 404)

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

@app.route("/api/user/me", methods=["PATCH", "OPTIONS"])
def patch_me():
    # ✅ 预检兜底
    if request.method == "OPTIONS":
        return ("", 204)

    uid = get_uid()
    if not uid:
        return fail("missing X-User-Id", 401)

    user = User.query.get(uid)
    if not user:
        return fail("user not found", 404)

    payload = request.get_json(silent=True) or {}

    # ✅ 白名单字段（只允许这些被更新）
    allowed = {
        "nickname", "gender", "bio", "phone",
        "school", "major", "job_title", "avatar_url"
    }

    updates = {k: payload.get(k) for k in payload if k in allowed}
    if not updates:
        return fail("no valid fields", 400)

    # ✅ 建议 gender 存 male/female（你前端可以传 male/female）
    if "gender" in updates:
        g = (updates["gender"] or "").strip()
        if g and g not in ["male", "female", "男", "女"]:
            return fail("invalid gender", 400)

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

if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # ⚠️ 只会创建缺失表，不会自动新增列（见下方说明）
    app.run(debug=True)
