import datetime

from app.extensions import db


class GenerationLog(db.Model):
    __tablename__ = "generation_logs"

    id = db.Column(db.Integer, primary_key=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    workflow_id = db.Column(db.Integer, db.ForeignKey("lesson_workflows.id"), nullable=True, index=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey("lessons.id"), nullable=True, index=True)
    step_no = db.Column(db.Integer, nullable=True)
    parse_status = db.Column(db.String(32), nullable=False, default="unknown")
    validation_status = db.Column(db.String(32), nullable=False, default="unknown")
    math_status = db.Column(db.String(32), nullable=False, default="unknown")
    failure_reason = db.Column(db.Text, nullable=True)
    raw_output = db.Column(db.Text, nullable=True)
    extracted_output = db.Column(db.Text, nullable=True)
    need_review = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
