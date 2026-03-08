from app.extensions import db
import datetime
import json


class ResourcePublish(db.Model):
    __tablename__ = "resource_publications"

    id = db.Column(db.Integer, primary_key=True)
    resource_type = db.Column(db.String(32), nullable=False)  # lesson | exercise
    resource_id = db.Column(db.Integer, nullable=False)
    class_id = db.Column(db.Integer, nullable=False)
    student_ids = db.Column(db.Text, nullable=True)
    accuracy_rule = db.Column(db.Text, nullable=True)
    mode = db.Column(db.String(32), nullable=True)
    revoked = db.Column(db.Boolean, default=False)
    revoked_at = db.Column(db.DateTime, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        def _load(s):
            try:
                return json.loads(s) if s else None
            except Exception:
                return None

        return {
            "id": self.id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "class_id": self.class_id,
            "student_ids": _load(self.student_ids),
            "accuracy_rule": _load(self.accuracy_rule),
            "mode": self.mode,
            "revoked": bool(self.revoked),
            "revoked_at": self.revoked_at.strftime("%Y-%m-%d %H:%M:%S") if self.revoked_at else "",
            "created_by": self.created_by,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else ""
        }
