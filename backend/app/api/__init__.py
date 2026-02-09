from flask import Flask
from app.api.auth.routes import bp as auth_bp
from app.api.user.routes import bp as user_bp
from app.api.lesson.routes import bp as lesson_bp

def register_blueprints(app: Flask) -> None:
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(lesson_bp)
