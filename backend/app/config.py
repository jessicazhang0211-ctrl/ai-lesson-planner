import os
from dotenv import load_dotenv

load_dotenv()  # 读取 backend/.env

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
    # JWT 设置
    JWT_SECRET = os.getenv("JWT_SECRET", None) or SECRET_KEY
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXP_SECONDS = int(os.getenv("JWT_EXP_SECONDS", "3600"))
