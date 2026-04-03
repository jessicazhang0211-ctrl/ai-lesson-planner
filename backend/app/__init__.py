from flask import Flask, jsonify, request
from flask_cors import CORS
from app.config import Config
from app.extensions import db
from app.api import register_blueprints
from app.middlewares import register_error_handlers

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
        if origin and origin in allowed_origins:
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
        db.create_all()

    return app
