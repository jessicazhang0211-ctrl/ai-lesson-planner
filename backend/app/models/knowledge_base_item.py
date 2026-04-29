from app.extensions import db
import datetime


class KnowledgeBaseItem(db.Model):
    __tablename__ = "knowledge_base_items"

    id = db.Column(db.Integer, primary_key=True)
    created_by = db.Column(db.Integer, nullable=False, index=True)
    class_id = db.Column(db.Integer, nullable=True, index=True)

    topic = db.Column(db.String(255), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=True)
    content = db.Column(db.Text, nullable=False)
    tags_json = db.Column(db.Text, nullable=True)
    source = db.Column(db.String(64), nullable=False, default="manual")

    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )
