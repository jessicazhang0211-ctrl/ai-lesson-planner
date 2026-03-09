from flask import Flask
from app.api.auth.routes import bp as auth_bp
from app.api.user.routes import bp as user_bp

from app.api.lesson.routes import bp as lesson_bp
from app.api.exercise.routes import bp as exercise_bp
from app.api.class_.routes import bp as class_bp
from app.api.resource.routes import bp as resource_bp
from app.api.student.routes import bp as student_bp

def register_blueprints(app: Flask) -> None:
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(lesson_bp)
    app.register_blueprint(exercise_bp)
    app.register_blueprint(class_bp)
    app.register_blueprint(resource_bp)
    app.register_blueprint(student_bp)
