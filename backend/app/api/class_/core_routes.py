from .shared import *
from .shared import _get_uid, _gen_code
from app.models.user import User
from app.models.exercise import Exercise
from app.config import Config
from app.services.ai_service import ai_service
from app.utils.json_handlers import extract_json


# In-process cache: recompute AI advice only when score signature changes.
_TEACHER_ADVICE_CACHE = {}


def _build_advice_signature(assignments):
    if not assignments:
        return (0, 0, 0, 0, "")

    total = len(assignments)
    completed = 0
    score_count = 0
    score_sum = 0
    latest_ts = ""

    for a in assignments:
        if a.status == "completed":
            completed += 1
        if a.score is not None:
            score_count += 1
            score_sum += int(a.score)
        t = a.completed_at or a.created_at
        if t:
            s = t.isoformat()
            if s > latest_ts:
                latest_ts = s

    return (total, completed, score_count, score_sum, latest_ts)


def _get_cached_teacher_advice(uid, signature):
    cached = _TEACHER_ADVICE_CACHE.get(uid)
    if not cached:
        return None
    if cached.get("signature") != signature:
        return None
    advice = cached.get("advice")
    if isinstance(advice, list) and advice:
        return advice
    return None


def _set_cached_teacher_advice(uid, signature, advice):
    _TEACHER_ADVICE_CACHE[uid] = {
        "signature": signature,
        "advice": advice,
    }


def _fallback_teacher_advice(weak_topics, submit_rate, accuracy_avg):
    advice = []
    if weak_topics:
        top = weak_topics[0]
        advice.append(
            f"优先加强《{top['topic']}》讲解，当前提交率{top['submit']}%、正确率{top['accuracy']}%。"
        )
        if len(weak_topics) > 1:
            t2 = weak_topics[1]
            advice.append(
                f"补充《{t2['topic']}》分层练习，先讲核心概念再做变式巩固。"
            )
    else:
        advice.append("近7天未发现明显薄弱课程，可保持当前教学节奏并做阶段复盘。")

    if submit_rate < 75:
        advice.append("作业提交率偏低，建议布置课堂当堂小测并设置次日追交机制。")
    if accuracy_avg < 75:
        advice.append("整体正确率偏低，建议在新课前加入5-8分钟基础回顾与错因讲评。")

    if not advice:
        advice.append("保持现有教学安排，持续跟踪每周提交率和正确率变化。")
    return advice[:4]


def _build_teacher_advice(weak_topics, class_rows, overview):
    submit_rate = int((overview or {}).get("submitRate", 0) or 0)
    accuracy_avg = int((overview or {}).get("accuracyAvg", 0) or 0)
    fallback = _fallback_teacher_advice(weak_topics, submit_rate, accuracy_avg)

    if not Config.GEMINI_API_KEY:
        return fallback

    weak_text = "；".join([
        f"{x['topic']}（提交率{x['submit']}%，正确率{x['accuracy']}%，班级{x['className']}）"
        for x in weak_topics[:5]
    ]) or "暂无明显薄弱课程"
    class_text = "；".join([
        f"{c['name']}：提交{int(round((c['submitted'] / c['total']) * 100)) if c['total'] else 0}%/正确{c['accuracy']}%"
        for c in class_rows[:8]
    ]) or "暂无班级数据"

    prompt = (
        "你是小学数学教学督导助手。基于以下学情摘要，输出对任课教师的改进建议。\n"
        "要求：\n"
        "1) 重点指出掌握薄弱的课程/题型并说明需要加强讲解；\n"
        "2) 给出可执行、可落地的课堂策略；\n"
        "3) 只输出 JSON：{\"advice\":[\"...\",\"...\"]}；\n"
        "4) advice 返回 3-4 条，每条不超过45字。\n\n"
        f"近7天总提交率：{submit_rate}%\n"
        f"近7天平均正确率：{accuracy_avg}%\n"
        f"薄弱课程/题型：{weak_text}\n"
        f"班级概览：{class_text}\n"
    )
    try:
        ai_text = ai_service.generate_text(prompt, model_name=Config.EXERCISE_GENERATION_MODEL)
        data = extract_json(ai_text)
        if isinstance(data, dict) and isinstance(data.get("advice"), list):
            advice = [str(x).strip() for x in data.get("advice", []) if str(x).strip()]
            if advice:
                return advice[:4]
    except Exception:
        pass

    return fallback

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


@bp.route("/public", methods=["GET"])
def list_public_classes():
    classes = Classroom.query.filter_by(status="active").order_by(Classroom.created_at.desc()).all()
    return ok([{"id": c.id, "name": c.name} for c in classes])


@bp.route("/overview", methods=["GET"])
@token_required
def teacher_overview():
    uid = int(getattr(g, "current_user_id", 0) or 0)
    if not uid:
        return err("missing user", http_status=401)

    classes = Classroom.query.filter_by(created_by=uid).order_by(Classroom.created_at.desc()).all()
    if not classes:
        return ok({
            "overview": {"students": 0, "active": 0, "submitRate": 0, "accuracyAvg": 0, "risk": 0},
            "monthly": [],
            "weekly": [],
            "praises": [],
            "risks": [],
            "teacherAdvice": ["暂无班级数据，建议先发布一次基础练习后再查看 AI 教学建议。"],
            "weakTopics": [],
            "classes": []
        })

    class_ids = [c.id for c in classes]
    class_name_map = {c.id: c.name for c in classes}

    students = Student.query.filter(Student.class_id.in_(class_ids)).all() if class_ids else []
    students_by_class = {}
    for s in students:
        students_by_class.setdefault(s.class_id, []).append(s)

    pubs = ResourcePublish.query.filter(
        ResourcePublish.class_id.in_(class_ids),
        ResourcePublish.revoked == False,
        ResourcePublish.resource_type == "exercise"
    ).all() if class_ids else []
    pub_map = {p.id: p for p in pubs}
    pub_ids = [p.id for p in pubs]

    assignments = ResourceAssignment.query.filter(ResourceAssignment.publish_id.in_(pub_ids)).all() if pub_ids else []
    assignments_by_class = {}
    for a in assignments:
        pub = pub_map.get(a.publish_id)
        if not pub:
            continue
        assignments_by_class.setdefault(pub.class_id, []).append(a)

    now = datetime.datetime.now()
    week_start = now - datetime.timedelta(days=7)
    month_start = now - datetime.timedelta(days=30)

    week_assignments = [a for a in assignments if (a.completed_at or a.created_at) and (a.completed_at or a.created_at) >= week_start]
    week_completed = [a for a in week_assignments if a.status == "completed"]

    total_students = len(students)
    active_students = len({a.student_id for a in week_completed})
    submit_rate = int(round((len(week_completed) / len(week_assignments)) * 100)) if week_assignments else 0
    week_scores = [a.score for a in week_completed if a.score is not None]
    accuracy_avg = int(round(sum(week_scores) / len(week_scores))) if week_scores else 0

    # monthly trend (last 30 days)
    monthly = []
    for i in range(29, -1, -1):
        day = (now - datetime.timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day + datetime.timedelta(days=1)
        day_items = [a for a in assignments if (a.completed_at or a.created_at) and day <= (a.completed_at or a.created_at) < day_end]
        day_completed = [a for a in day_items if a.status == "completed"]
        day_submit = int(round((len(day_completed) / len(day_items)) * 100)) if day_items else 0
        day_scores = [a.score for a in day_completed if a.score is not None]
        day_acc = int(round(sum(day_scores) / len(day_scores))) if day_scores else 0
        monthly.append({
            "day": day.strftime("%m-%d"),
            "submit": day_submit,
            "accuracy": day_acc
        })

    # weekly trend (last 7 days)
    weekly = []
    for i in range(6, -1, -1):
        day = (now - datetime.timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day + datetime.timedelta(days=1)
        day_items = [a for a in assignments if (a.completed_at or a.created_at) and day <= (a.completed_at or a.created_at) < day_end]
        day_completed = [a for a in day_items if a.status == "completed"]
        day_submit = int(round((len(day_completed) / len(day_items)) * 100)) if day_items else 0
        day_scores = [a.score for a in day_completed if a.score is not None]
        day_acc = int(round(sum(day_scores) / len(day_scores))) if day_scores else 0
        weekly.append({
            "day": day.strftime("%m-%d"),
            "submit": day_submit,
            "accuracy": day_acc
        })

    # per-student week stats
    week_map = {}
    for a in week_assignments:
        key = a.student_id
        item = week_map.setdefault(key, {"total": 0, "completed": 0, "scores": []})
        item["total"] += 1
        if a.status == "completed":
            item["completed"] += 1
        if a.score is not None:
            item["scores"].append(a.score)

    # latest scores (overall)
    latest_score_map = {}
    for a in assignments:
        if a.score is None:
            continue
        t = a.completed_at or a.created_at
        if not t:
            continue
        latest_score_map.setdefault(a.student_id, []).append({"score": a.score, "time": t})

    # risk list (last 7 days)
    risk_map = {}
    for a in week_assignments:
        key = a.student_id
        item = risk_map.setdefault(key, {"total": 0, "completed": 0, "scores": [], "latest_scores": []})
        item["total"] += 1
        if a.status == "completed":
            item["completed"] += 1
        if a.score is not None:
            item["scores"].append(a.score)
            item["latest_scores"].append({
                "score": a.score,
                "time": a.completed_at or a.created_at
            })

    student_map = {s.id: s for s in students}
    risks = []
    for sid, info in risk_map.items():
        total = info["total"]
        submit = int(round((info["completed"] / total) * 100)) if total else 0
        scores = info["scores"]
        avg_score = int(round(sum(scores) / len(scores))) if scores else 0
        drop_flag = False
        if info["latest_scores"]:
            latest = sorted(
                [x for x in info["latest_scores"] if x.get("time")],
                key=lambda x: x["time"],
                reverse=True
            )
            if len(latest) >= 2:
                if (latest[0]["score"] - latest[1]["score"]) <= -20:
                    drop_flag = True

        if submit < 60 or avg_score < 60 or drop_flag:
            student = student_map.get(sid)
            if not student:
                continue
            tag = "danger" if submit < 50 or avg_score < 55 or drop_flag else "warn"
            risks.append({
                "name": student.name,
                "className": class_name_map.get(student.class_id, ""),
                "submit": submit,
                "accuracy": avg_score,
                "tag": tag
            })
    risks = sorted(risks, key=lambda x: (x["tag"] != "danger", x["submit"], x["accuracy"]))

    # praise list (last 7 days submit/accuracy or score improvement)
    praises = []
    for sid in set(list(week_map.keys()) + list(latest_score_map.keys())):
        student = student_map.get(sid)
        if not student:
            continue
        w = week_map.get(sid, {"total": 0, "completed": 0, "scores": []})
        total = w["total"]
        completed = w["completed"]
        submit_rate_week = int(round((completed / total) * 100)) if total else 0
        scores_week = w["scores"]
        avg_week = int(round(sum(scores_week) / len(scores_week))) if scores_week else 0

        improved = False
        latest = latest_score_map.get(sid, [])
        if latest:
            latest_sorted = sorted(latest, key=lambda x: x["time"], reverse=True)
            if len(latest_sorted) >= 2:
                if (latest_sorted[0]["score"] - latest_sorted[1]["score"]) >= 5:
                    improved = True

        praise_flag = (total > 0 and completed == total) or (avg_week >= 80) or improved
        if not praise_flag:
            continue

        praises.append({
            "name": student.name,
            "className": class_name_map.get(student.class_id, ""),
            "submit": submit_rate_week,
            "accuracy": avg_week,
            "tag": "praise"
        })

    class_rows = []
    for c in classes:
        cls_students = students_by_class.get(c.id, [])
        total = len(cls_students)
        pending = len([s for s in cls_students if s.status == "pending"])
        cls_assignments = assignments_by_class.get(c.id, [])
        cls_completed = [a for a in cls_assignments if a.status == "completed"]
        submitted_students = len({a.student_id for a in cls_completed})
        cls_scores = [a.score for a in cls_completed if a.score is not None]
        cls_accuracy = int(round(sum(cls_scores) / len(cls_scores))) if cls_scores else 0
        cls_risk = len([r for r in risks if r["className"] == c.name])
        class_rows.append({
            "id": c.id,
            "name": c.name,
            "total": total,
            "submitted": submitted_students,
            "accuracy": cls_accuracy,
            "risk": cls_risk,
            "pending": pending
        })

    # weak topics for teacher advice (aggregate from last 7 days assignments by exercise title)
    exercise_ids = list({p.resource_id for p in pubs if p.resource_id})
    exercise_map = {}
    if exercise_ids:
        exercise_rows = Exercise.query.filter(Exercise.id.in_(exercise_ids)).all()
        exercise_map = {e.id: e.title for e in exercise_rows}

    weak_topic_map = {}
    for a in week_assignments:
        pub = pub_map.get(a.publish_id)
        if not pub:
            continue
        topic_name = (exercise_map.get(pub.resource_id) or f"练习#{pub.resource_id}").strip()
        item = weak_topic_map.setdefault(topic_name, {
            "topic": topic_name,
            "class_names": set(),
            "total": 0,
            "completed": 0,
            "scores": []
        })
        item["total"] += 1
        item["class_names"].add(class_name_map.get(pub.class_id, ""))
        if a.status == "completed":
            item["completed"] += 1
        if a.score is not None:
            item["scores"].append(a.score)

    weak_topics = []
    for _, item in weak_topic_map.items():
        submit = int(round((item["completed"] / item["total"]) * 100)) if item["total"] else 0
        accuracy = int(round(sum(item["scores"]) / len(item["scores"]))) if item["scores"] else 0
        if submit < 75 or accuracy < 75:
            weak_topics.append({
                "topic": item["topic"],
                "submit": submit,
                "accuracy": accuracy,
                "className": "、".join([x for x in sorted(item["class_names"]) if x])
            })
    weak_topics = sorted(weak_topics, key=lambda x: (x["accuracy"], x["submit"]))[:5]

    advice_signature = _build_advice_signature(assignments)
    teacher_advice = _get_cached_teacher_advice(uid, advice_signature)
    if not teacher_advice:
        teacher_advice = _build_teacher_advice(
            weak_topics,
            class_rows,
            {
                "submitRate": submit_rate,
                "accuracyAvg": accuracy_avg,
            }
        )
        _set_cached_teacher_advice(uid, advice_signature, teacher_advice)

    return ok({
        "overview": {
            "students": total_students,
            "active": active_students,
            "submitRate": submit_rate,
            "accuracyAvg": accuracy_avg,
            "risk": len(risks)
        },
        "monthly": monthly,
        "weekly": weekly,
        "praises": praises,
        "risks": risks,
        "teacherAdvice": teacher_advice,
        "weakTopics": weak_topics,
        "classes": class_rows
    })


@bp.route("/", methods=["POST"])
def create_class():
    uid = _get_uid()
    if not uid:
        return err("missing X-User-Id", http_status=401)
    if not User.query.get(uid):
        return err("invalid user", http_status=401)

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

    # compute per-student accuracy/submit from published exercise assignments
    students = c.students or []
    pubs = ResourcePublish.query.filter_by(class_id=cid, revoked=False, resource_type='exercise').all()
    pub_ids = [p.id for p in pubs]
    assignments = ResourceAssignment.query.filter(ResourceAssignment.publish_id.in_(pub_ids)).all() if pub_ids else []
    stat_map = {}
    for a in assignments:
        item = stat_map.setdefault(a.student_id, {"total": 0, "completed": 0, "scores": []})
        item["total"] += 1
        if a.status == 'completed':
            item["completed"] += 1
        if a.score is not None:
            item["scores"].append(a.score)

    student_rows = []
    for s in students:
        base = s.to_dict()
        info = stat_map.get(s.id, {"total": 0, "completed": 0, "scores": []})
        total = info["total"]
        completed = info["completed"]
        submit = int(round((completed / total) * 100)) if total else base.get('submit')
        scores = info["scores"]
        avg_score = int(round(sum(scores) / len(scores))) if scores else base.get('accuracy')
        base['submit'] = submit
        base['accuracy'] = avg_score
        student_rows.append(base)

    data = c.to_dict(include_students=False)
    data['students'] = student_rows
    return ok(data)


@bp.route('/<int:cid>/stats/basic', methods=['GET'])
def class_stats_basic(cid: int):
    uid = _get_uid()
    if not uid:
        return err('missing X-User-Id', http_status=401)
    c = Classroom.query.get(cid)
    if not c or c.created_by != uid:
        return err('class not found', http_status=404)

    pubs = ResourcePublish.query.filter_by(class_id=cid, revoked=False, resource_type='exercise').all()
    pub_ids = [p.id for p in pubs]
    assignments = ResourceAssignment.query.filter(ResourceAssignment.publish_id.in_(pub_ids)).all() if pub_ids else []

    total = len(assignments)
    completed = len([a for a in assignments if a.status == 'completed'])
    submission_rate = int(round((completed / total) * 100)) if total else 0

    scores = [a.score for a in assignments if a.score is not None]
    avg_score = int(round(sum(scores) / len(scores))) if scores else None

    return ok({
        'class_id': cid,
        'submission_rate': submission_rate,
        'completed': completed,
        'total': total,
        'avg_score': avg_score
    })


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


@bp.route('/<int:cid>/students/<int:sid>', methods=['GET'])
def get_student(cid: int, sid: int):
    uid = _get_uid()
    if not uid:
        return err('missing X-User-Id', http_status=401)
    c = Classroom.query.get(cid)
    if not c or c.created_by != uid:
        return err('class not found', http_status=404)
    s = Student.query.get(sid)
    if not s or s.class_id != cid:
        return err('student not found', http_status=404)
    return ok(s.to_dict())


def _gen_temp_password(n=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=n))


@bp.route('/<int:cid>/students/<int:sid>/reset-password', methods=['POST'])
def reset_student_password(cid: int, sid: int):
    """Demo endpoint: generate a temporary password for the student and return it.
    In a real system this would integrate with the auth/user table and send via SMS/email.
    """
    uid = _get_uid()
    if not uid:
        return err('missing X-User-Id', http_status=401)
    c = Classroom.query.get(cid)
    if not c or c.created_by != uid:
        return err('class not found', http_status=404)
    s = Student.query.get(sid)
    if not s or s.class_id != cid:
        return err('student not found', http_status=404)

    newpwd = _gen_temp_password(8)
    # Note: Student model doesn't store passwords. This is a demo-only response.
    return ok({'new_password': newpwd}, 'password reset (demo)')


@bp.route('/<int:cid>/students/<int:sid>/status', methods=['POST'])
def set_student_status(cid: int, sid: int):
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
    action = (data.get('action') or '').lower()
    if action == 'disable':
        s.status = 'disabled'
    elif action == 'enable':
        s.status = 'joined'
    else:
        return err('invalid action', http_status=400)
    db.session.commit()
    return ok({'status': s.status})


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



