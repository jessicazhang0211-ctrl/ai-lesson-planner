# app\models\user.py
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # profile/work fields (for settings page)
    nickname = db.Column(db.String(64), nullable=True)
    gender = db.Column(db.String(16), nullable=True)  # 建议存 male/female，前端翻译显示
    bio = db.Column(db.String(500), nullable=True)
    phone = db.Column(db.String(32), nullable=True)

    school = db.Column(db.String(128), nullable=True)
    major = db.Column(db.String(128), nullable=True)
    job_title = db.Column(db.String(128), nullable=True)

    avatar_url = db.Column(db.String(255), nullable=True)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)
