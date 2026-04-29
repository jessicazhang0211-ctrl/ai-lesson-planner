import datetime

from app.extensions import db


class LessonEditLog(db.Model):
    __tablename__ = "lesson_edit_logs"

    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey("lessons.id"), nullable=False, index=True)
    edited_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    version_from = db.Column(db.Integer, nullable=False)
    version_to = db.Column(db.Integer, nullable=False)
    before_content = db.Column(db.Text, nullable=True)
    after_content = db.Column(db.Text, nullable=True)
    diff_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
