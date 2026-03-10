from app.extensions import db
import datetime


class ResourceAssignment(db.Model):
    __tablename__ = "resource_assignments"

    id = db.Column(db.Integer, primary_key=True)
    publish_id = db.Column(db.Integer, db.ForeignKey("resource_publications.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("class_students.id"), nullable=False)
    status = db.Column(db.String(32), default="assigned")  # assigned | saved | completed
    score = db.Column(db.Integer, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "publish_id": self.publish_id,
            "student_id": self.student_id,
            "status": self.status,
            "score": self.score,
            "completed_at": self.completed_at.strftime("%Y-%m-%d %H:%M:%S") if self.completed_at else "",
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else ""
        }
