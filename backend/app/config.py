import os
from dotenv import load_dotenv

load_dotenv(override=True)  # 读取 backend/.env，并覆盖已存在的系统环境变量

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")

    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_NAME = os.getenv("DB_NAME", "ai_lesson_planner")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")

    # SQLAlchemy MySQL URI (PyMySQL)
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        "?charset=utf8mb4"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Google Gemini API (免费额度：60 请求/分钟)
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

    # OpenAI API（教案生成专用）
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

    # 资源类型分模型配置：教案迁移到 GPT-5-mini，其他保持 Gemini
    LESSON_GENERATION_MODEL = os.getenv("LESSON_GENERATION_MODEL", "gpt-5-mini")
    EXERCISE_GENERATION_MODEL = os.getenv("EXERCISE_GENERATION_MODEL", "gemini-2.5-flash")
    LESSON_MAX_COMPLETION_TOKENS = int(os.getenv("LESSON_MAX_COMPLETION_TOKENS", "12000"))
    # JWT 设置
    JWT_SECRET = os.getenv("JWT_SECRET", None) or SECRET_KEY
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXP_SECONDS = int(os.getenv("JWT_EXP_SECONDS", "3600"))
    ENABLE_GLOBAL_ERROR_HANDLER = os.getenv("ENABLE_GLOBAL_ERROR_HANDLER", "0") == "1"

    # CORS 白名单，逗号分隔；为空时仅允许本地常见前端端口
    _cors_raw = os.getenv("CORS_ORIGINS", "").strip()
    if _cors_raw:
        CORS_ORIGINS = [x.strip() for x in _cors_raw.split(",") if x.strip()]
    else:
        CORS_ORIGINS = [
            "http://127.0.0.1:8000",
            "http://localhost:8000",
            "http://127.0.0.1:5500",
            "http://localhost:5500",
        ]
