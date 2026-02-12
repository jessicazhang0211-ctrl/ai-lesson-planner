from app.extensions import db
import datetime


class Classroom(db.Model):
    __tablename__ = 'classes'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(32), default='active')  # active | archived
    code = db.Column(db.String(64), nullable=True, index=True)
    created_at = db.Column(db.DateTime, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    stage = db.Column(db.String(64), nullable=True)
    allow_join = db.Column(db.Boolean, default=True)
    note = db.Column(db.String(500), nullable=True)

    students = db.relationship('Student', backref='classroom', cascade='all, delete-orphan')

    def to_dict(self, include_students=False):
        obj = {
            'id': self.id,
            'name': self.name,
            'desc': self.description or '',
            'status': self.status,
            'code': self.code or '',
            'created_at': self.created_at.strftime('%Y-%m-%d') if self.created_at else '',
            'stage': self.stage or '',
            'allow_join': bool(self.allow_join),
            'note': self.note or ''
        }
        if include_students:
            obj['students'] = [s.to_dict() for s in self.students]
        return obj


class Student(db.Model):
    __tablename__ = 'class_students'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    stu_id = db.Column(db.String(64), nullable=True)
    status = db.Column(db.String(32), default='joined')  # joined | pending | disabled
    parent_phone = db.Column(db.String(64), nullable=True)
    accuracy = db.Column(db.Integer, nullable=True)
    submit = db.Column(db.Integer, nullable=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'stu_id': self.stu_id or '',
            'status': self.status,
            'parent_phone': self.parent_phone or '',
            'accuracy': self.accuracy,
            'submit': self.submit,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else ''
        }
