from flask import Flask, jsonify, request
from flask_cors import CORS
import fnmatch
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError
from app.config import Config
from app.extensions import db
from app.api import register_blueprints
from app.middlewares import register_error_handlers


def _origin_allowed(origin, allowed_origins):
    if not origin:
        return False
    if "*" in allowed_origins:
        return True
    for pattern in allowed_origins:
        if pattern == origin:
            return True
        if "*" in pattern and fnmatch.fnmatch(origin, pattern):
            return True
    return False


def _ensure_student_profile_schema():
    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())
    if "student_profiles" not in tables:
        return

    existing = {col["name"] for col in inspector.get_columns("student_profiles")}
    required_cols = {
        "knowledge_stats_json": "TEXT NULL",
        "error_type_stats_json": "TEXT NULL",
        "recommendation_text": "TEXT NULL",
        "analysis_latest_completed_at": "DATETIME NULL",
    }

    missing = [(name, ddl) for name, ddl in required_cols.items() if name not in existing]
    if not missing:
        return

    with db.engine.begin() as conn:
        for name, ddl in missing:
            try:
                conn.execute(text(f"ALTER TABLE student_profiles ADD COLUMN {name} {ddl}"))
            except OperationalError as e:
                # Flask debug reloader may start two processes concurrently; ignore duplicate-column race.
                code = None
                if getattr(e, "orig", None) is not None and getattr(e.orig, "args", None):
                    code = e.orig.args[0]
                msg = str(e).lower()
                if code == 1060 or "duplicate column name" in msg:
                    continue
                raise


def _ensure_lessons_schema():
    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())
    if "lessons" not in tables:
        return

    existing = {col["name"] for col in inspector.get_columns("lessons")}
    required_cols = {
        "version": "INT NOT NULL DEFAULT 1",
        "root_lesson_id": "INT NULL",
        "parent_lesson_id": "INT NULL",
    }

    missing = [(name, ddl) for name, ddl in required_cols.items() if name not in existing]
    if not missing:
        return

    with db.engine.begin() as conn:
        for name, ddl in missing:
            try:
                conn.execute(text(f"ALTER TABLE lessons ADD COLUMN {name} {ddl}"))
            except OperationalError as e:
                # Flask debug reloader may start two processes concurrently; ignore duplicate-column race.
                code = None
                if getattr(e, "orig", None) is not None and getattr(e.orig, "args", None):
                    code = e.orig.args[0]
                msg = str(e).lower()
                if code == 1060 or "duplicate column name" in msg:
                    continue
                raise

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # 允许跨域（前后端分离必备）
    allowed_origins = app.config.get("CORS_ORIGINS", []) or []
    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": allowed_origins,
                "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization", "X-Requested-With", "X-User-Id"],
                "supports_credentials": False,
            }
        },
    )

    @app.after_request
    def add_cors_headers(resp):
        # Some early-return/error paths may skip flask-cors matching; add a safe fallback for /api/*.
        if not (request.path or "").startswith("/api/"):
            return resp

        origin = request.headers.get("Origin", "")
        if _origin_allowed(origin, allowed_origins):
            resp.headers["Access-Control-Allow-Origin"] = origin
            resp.headers["Vary"] = "Origin"
            resp.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
            resp.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization,X-Requested-With,X-User-Id"
        return resp

    # 初始化数据库
    db.init_app(app)

    # 注册路由
    register_blueprints(app)

    if app.config.get("ENABLE_GLOBAL_ERROR_HANDLER"):
        register_error_handlers(app)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    @app.get("/api/diag/routes")
    def diag_routes():
        routes = sorted({rule.rule for rule in app.url_map.iter_rules()})
        return jsonify({"routes": routes})

    # ✅ 启动时建表（开发阶段最省事，后面可升级迁移）
    with app.app_context():
        _ensure_student_profile_schema()
        db.create_all()
        _ensure_lessons_schema()

    return app
