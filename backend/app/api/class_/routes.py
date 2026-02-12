from flask import Blueprint, request
from app.utils.response import ok, err
from app.extensions import db
from app.models.classroom import Classroom, Student
import datetime, random, string

bp = Blueprint("class", __name__, url_prefix="/api/class")


def _gen_code(n=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=n))


def _get_uid():
    uid = (request.headers.get("X-User-Id") or "").strip()
    try:
        return int(uid) if uid else None
    except ValueError:
        return None


@bp.route("/", methods=["GET"])
def list_classes():
    uid = _get_uid()
    if not uid:
        return err("missing X-User-Id", http_status=401)

    status = request.args.get('status')  # optional filter
    q = Classroom.query.filter_by(created_by=uid)
    if status in ("active", "archived"):
        q = q.filter_by(status=status)
    classes = q.order_by(Classroom.created_at.desc()).all()
    return ok([c.to_dict() for c in classes])


@bp.route("/", methods=["POST"])
def create_class():
    uid = _get_uid()
    if not uid:
        return err("missing X-User-Id", http_status=401)

    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return err('name required', http_status=400)

    c = Classroom(
        name=name,
        description=data.get('desc') or '',
        status='active',
        code=_gen_code(6),
        created_at=datetime.datetime.now(),
        created_by=uid,
        stage=data.get('stage') or '',
        allow_join=bool(data.get('allow_join', True)),
        note=data.get('note') or ''
    )
    db.session.add(c)
    db.session.commit()
    return ok(c.to_dict())


@bp.route('/<int:cid>', methods=['GET'])
def get_class(cid: int):
    uid = _get_uid()
    if not uid:
        return err('missing X-User-Id', http_status=401)
    c = Classroom.query.get(cid)
    if not c or c.created_by != uid:
        return err('class not found', http_status=404)
    return ok(c.to_dict(include_students=True))


@bp.route('/<int:cid>', methods=['PATCH'])
def update_class(cid: int):
    uid = _get_uid()
    if not uid:
        return err('missing X-User-Id', http_status=401)
    c = Classroom.query.get(cid)
    if not c or c.created_by != uid:
        return err('class not found', http_status=404)

    data = request.get_json(silent=True) or {}
    allowed = {'name', 'desc', 'stage', 'allow_join', 'note'}
    for k in allowed:
        if k in data:
            if k == 'desc':
                setattr(c, 'description', data.get(k))
            else:
                setattr(c, k, data.get(k))
    db.session.commit()
    return ok(c.to_dict())


@bp.route('/<int:cid>/archive', methods=['POST'])
def archive_class(cid: int):
    uid = _get_uid()
    if not uid:
        return err('missing X-User-Id', http_status=401)
    c = Classroom.query.get(cid)
    if not c or c.created_by != uid:
        return err('class not found', http_status=404)
    data = request.get_json(silent=True) or {}
    action = data.get('action', 'archive')
    if action == 'archive':
        c.status = 'archived'
    else:
        c.status = 'active'
    db.session.commit()
    return ok({'status': c.status})


@bp.route('/<int:cid>', methods=['DELETE'])
def delete_class(cid: int):
    uid = _get_uid()
    if not uid:
        return err('missing X-User-Id', http_status=401)
    c = Classroom.query.get(cid)
    if not c or c.created_by != uid:
        return err('class not found', http_status=404)
    db.session.delete(c)
    db.session.commit()
    return ok({'deleted': True}, 'deleted')


# Students
@bp.route('/<int:cid>/students', methods=['POST'])
def add_student(cid: int):
    uid = _get_uid()
    if not uid:
        return err('missing X-User-Id', http_status=401)
    c = Classroom.query.get(cid)
    if not c or c.created_by != uid:
        return err('class not found', http_status=404)
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return err('student name required', http_status=400)
    s = Student(
        name=name,
        stu_id=data.get('stu_id') or '',
        status=data.get('status') or 'joined',
        parent_phone=data.get('parent_phone') or '',
        accuracy=data.get('accuracy'),
        submit=data.get('submit'),
        class_id=cid
    )
    db.session.add(s)
    db.session.commit()
    return ok(s.to_dict())


@bp.route('/join', methods=['POST', 'OPTIONS'])
def join_by_code():
    if request.method == 'OPTIONS':
        return '', 204

    data = request.get_json(silent=True) or {}
    code = (data.get('code') or '').strip()
    name = (data.get('name') or '').strip()
    stu_id = (data.get('stu_id') or '').strip()
    parent_phone = (data.get('parent_phone') or '').strip()

    if not code or not name:
        return err('code and name required', http_status=400)

    cls = Classroom.query.filter_by(code=code, status='active').first()
    if not cls:
        return err('class not found or not joinable', http_status=404)
    if not cls.allow_join:
        return err('class does not allow join', http_status=403)

    s = Student(
        name=name,
        stu_id=stu_id or '',
        status='joined',
        parent_phone=parent_phone or '',
        class_id=cls.id
    )
    db.session.add(s)
    db.session.commit()

    return ok({'class': cls.to_dict(), 'student': s.to_dict()}, 'joined')




@bp.route('/<int:cid>/students/<int:sid>', methods=['PATCH'])
def update_student(cid: int, sid: int):
    uid = _get_uid()
    if not uid:
        return err('missing X-User-Id', http_status=401)
    c = Classroom.query.get(cid)
    if not c or c.created_by != uid:
        return err('class not found', http_status=404)
    s = Student.query.get(sid)
    if not s or s.class_id != cid:
        return err('student not found', http_status=404)
    data = request.get_json(silent=True) or {}
    for k in ('name', 'stu_id', 'status', 'parent_phone', 'accuracy', 'submit'):
        if k in data:
            setattr(s, k if k != 'parent_phone' else 'parent_phone', data.get(k))
    db.session.commit()
    return ok(s.to_dict())


@bp.route('/<int:cid>/students/<int:sid>', methods=['DELETE'])
def delete_student(cid: int, sid: int):
    uid = _get_uid()
    if not uid:
        return err('missing X-User-Id', http_status=401)
    c = Classroom.query.get(cid)
    if not c or c.created_by != uid:
        return err('class not found', http_status=404)
    s = Student.query.get(sid)
    if not s or s.class_id != cid:
        return err('student not found', http_status=404)
    db.session.delete(s)
    db.session.commit()
    return ok({'deleted': True}, 'deleted')


@bp.route('/<int:cid>/reset-code', methods=['POST'])
def reset_class_code(cid: int):
    uid = _get_uid()
    if not uid:
        return err('missing X-User-Id', http_status=401)
    c = Classroom.query.get(cid)
    if not c or c.created_by != uid:
        return err('class not found', http_status=404)
    c.code = _gen_code(6)
    db.session.commit()
    return ok({'code': c.code}, 'code reset')
