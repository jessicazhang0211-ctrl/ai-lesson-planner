import datetime

from app.extensions import db


class LessonWorkflow(db.Model):
    __tablename__ = "lesson_workflows"

    id = db.Column(db.Integer, primary_key=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    topic = db.Column(db.String(255), nullable=True)
    subject = db.Column(db.String(128), nullable=True)
    grade = db.Column(db.String(128), nullable=True)
    current_step = db.Column(db.Integer, nullable=False, default=1)
    is_completed = db.Column(db.Boolean, nullable=False, default=False)
    # JSON object serialized as string:
    # {"step_1": "pending|completed|need_review|failed", ... "step_6": ...}
    status_json = db.Column(db.Text, nullable=True)
    # JSON object serialized as string:
    # {"step_1": "generated content", ...}
    content_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )
