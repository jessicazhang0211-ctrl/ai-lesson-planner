from app.extensions import db
import datetime


class ExerciseSubmission(db.Model):
    __tablename__ = "exercise_submissions"

    id = db.Column(db.Integer, primary_key=True)
    publish_id = db.Column(db.Integer, db.ForeignKey("resource_publications.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("class_students.id"), nullable=False)
    answers = db.Column(db.Text, nullable=True)
    auto_result = db.Column(db.Text, nullable=True)
    auto_score = db.Column(db.Integer, nullable=True)
    teacher_score = db.Column(db.Integer, nullable=True)
    total_score = db.Column(db.Integer, nullable=True)
    teacher_comment = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(32), default="pending_review")  # saved | pending_review | graded
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "publish_id": self.publish_id,
            "student_id": self.student_id,
            "auto_score": self.auto_score,
            "teacher_score": self.teacher_score,
            "total_score": self.total_score,
            "teacher_comment": self.teacher_comment or "",
            "status": self.status,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "",
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else ""
        }
