from app.extensions import db
import datetime


class StudentProfile(db.Model):
    __tablename__ = "student_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("class_students.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    analysis_json = db.Column(db.Text, nullable=True)
    analysis_updated_at = db.Column(db.DateTime, nullable=True)
    analysis_latest_completed_at = db.Column(db.DateTime, nullable=True)
    knowledge_stats_json = db.Column(db.Text, nullable=True)
    error_type_stats_json = db.Column(db.Text, nullable=True)
    recommendation_text = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "class_id": self.class_id,
            "student_id": self.student_id,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "",
            "recommendation_text": self.recommendation_text or "",
        }