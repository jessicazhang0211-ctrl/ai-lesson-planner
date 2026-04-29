import datetime

from app.extensions import db


class ValidationLog(db.Model):
    __tablename__ = "validation_logs"

    id = db.Column(db.Integer, primary_key=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    entity_type = db.Column(db.String(32), nullable=False, index=True)  # lesson | exercise
    entity_id = db.Column(db.Integer, nullable=True, index=True)

    workflow_id = db.Column(db.Integer, db.ForeignKey("lesson_workflows.id"), nullable=True, index=True)
    step_no = db.Column(db.Integer, nullable=True)

    parse_status = db.Column(db.String(32), nullable=False, default="unknown")
    validation_status = db.Column(db.String(32), nullable=False, default="unknown")
    need_review = db.Column(db.Boolean, nullable=False, default=False)

    reasons_json = db.Column(db.Text, nullable=True)
    review_reason = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
