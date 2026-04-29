from app.extensions import db
import datetime


class AssignmentAnalysis(db.Model):
    __tablename__ = "assignment_analyses"

    id = db.Column(db.Integer, primary_key=True)
    created_by = db.Column(db.Integer, nullable=False, index=True)
    class_id = db.Column(db.Integer, nullable=True, index=True)
    publish_id = db.Column(db.Integer, nullable=False, index=True)
    submission_id = db.Column(db.Integer, nullable=False, unique=True, index=True)
    exercise_id = db.Column(db.Integer, nullable=True, index=True)

    topic = db.Column(db.String(255), nullable=True)
    title = db.Column(db.String(255), nullable=True)

    score = db.Column(db.Integer, nullable=True)
    max_score = db.Column(db.Integer, nullable=True)
    completion_rate = db.Column(db.Float, nullable=True)

    weak_question_types_json = db.Column(db.Text, nullable=True)
    common_misconceptions_json = db.Column(db.Text, nullable=True)
    analysis_json = db.Column(db.Text, nullable=True)
    summary_text = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )
