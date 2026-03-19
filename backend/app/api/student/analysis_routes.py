from .shared import *
from .shared import _rule_based_analysis, _ai_analysis

@bp.route("/overview", methods=["GET"])
@token_required
def overview():
    user_id = int(getattr(g, "current_user_id", 0) or 0)
    if not user_id:
        return err("missing user", http_status=401)

    profile = StudentProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        return err("student profile not found", http_status=404)

    pubs = ResourcePublish.query.filter_by(class_id=profile.class_id, revoked=False, resource_type="exercise").all()
    pub_ids = [p.id for p in pubs]
    pub_map = {p.id: p for p in pubs}
    exercise_ids = [p.resource_id for p in pubs]
    exercises = {e.id: e for e in Exercise.query.filter(Exercise.id.in_(exercise_ids)).all()} if exercise_ids else {}
    assignments = ResourceAssignment.query.filter(
        ResourceAssignment.publish_id.in_(pub_ids),
        ResourceAssignment.student_id == profile.student_id
    ).all() if pub_ids else []

    total = len(assignments)
    completed_list = [a for a in assignments if a.status == "completed"]
    completed = len(completed_list)
    submission_rate = int(round((completed / total) * 100)) if total else 0

    scores_all = [a.score for a in assignments if a.score is not None]
    avg_score_all = int(round(sum(scores_all) / len(scores_all))) if scores_all else None

    now = datetime.datetime.now()
    week_start = now - datetime.timedelta(days=7)
    scores_week = [a.score for a in assignments if a.score is not None and (a.completed_at or a.created_at) and (a.completed_at or a.created_at) >= week_start]
    avg_score_week = int(round(sum(scores_week) / len(scores_week))) if scores_week else None

    latest_score = None
    completed_with_time = [a for a in assignments if a.score is not None]
    if completed_with_time:
        completed_with_time.sort(key=lambda x: x.completed_at or x.created_at, reverse=True)
        latest_score = completed_with_time[0].score

    trend_items = []
    if completed_with_time:
        completed_with_time.sort(key=lambda x: x.completed_at or x.created_at)
        for a in completed_with_time[-10:]:
            dt = a.completed_at or a.created_at
            label = dt.strftime("%m-%d") if dt else ""
            pub = pub_map.get(a.publish_id)
            ex = exercises.get(pub.resource_id) if pub else None
            trend_items.append({
                "label": label,
                "score": a.score,
                "title": ex.title if ex else ""
            })

    # weak point analysis
    wrong_total_by_type = {}
    total_by_type = {}
    if pub_ids:
        submissions = (ExerciseSubmission.query
            .filter(ExerciseSubmission.publish_id.in_(pub_ids), ExerciseSubmission.student_id == profile.student_id)
            .order_by(ExerciseSubmission.updated_at.desc())
            .limit(10)
            .all())
        pub_map = pub_map or {p.id: p for p in pubs}
        exercises = exercises or {e.id: e for e in Exercise.query.filter(Exercise.id.in_(exercise_ids)).all()} if exercise_ids else {}

        for s in submissions:
            if not s.auto_result:
                continue
            pub = pub_map.get(s.publish_id)
            if not pub:
                continue
            ex = exercises.get(pub.resource_id)
            if not ex or not ex.content_json:
                continue
            try:
                structured = json.loads(ex.content_json)
                auto_result = json.loads(s.auto_result)
            except Exception:
                continue
            for q in structured.get("questions", []):
                qid = q.get("id")
                qtype = (q.get("type") or "").lower()
                if qtype in ("short", "essay"):
                    continue
                total_by_type[qtype] = total_by_type.get(qtype, 0) + 1
                if auto_result.get(qid) == "wrong":
                    wrong_total_by_type[qtype] = wrong_total_by_type.get(qtype, 0) + 1

    wrong_rate_map = {}
    for k, total_cnt in total_by_type.items():
        wrong_cnt = wrong_total_by_type.get(k, 0)
        if total_cnt:
            wrong_rate_map[k] = wrong_cnt / total_cnt

    latest_completed_at = None
    if completed_with_time:
        latest_completed_at = max([a.completed_at or a.created_at for a in completed_with_time if (a.completed_at or a.created_at)], default=None)

    cached_analysis = None
    if profile.analysis_json:
        try:
            cached_analysis = json.loads(profile.analysis_json)
        except Exception:
            cached_analysis = None

    should_recompute = False
    if not cached_analysis:
        should_recompute = True
    elif latest_completed_at and (not profile.analysis_latest_completed_at or latest_completed_at > profile.analysis_latest_completed_at):
        should_recompute = True

    analysis = cached_analysis or _rule_based_analysis(avg_score_all, wrong_rate_map)
    if should_recompute:
        analysis = _rule_based_analysis(avg_score_all, wrong_rate_map)
        summary_text = (
            f"提交率{submission_rate}%，总平均分{avg_score_all if avg_score_all is not None else '无'}，"
            f"本周平均分{avg_score_week if avg_score_week is not None else '无'}，"
            f"错题比例{ {k: round(v,2) for k,v in wrong_rate_map.items()} }"
        )
        ai_result = _ai_analysis(summary_text)
        if ai_result:
            analysis = ai_result

        profile.analysis_json = json.dumps(analysis, ensure_ascii=False)
        profile.analysis_updated_at = datetime.datetime.now()
        profile.analysis_latest_completed_at = latest_completed_at
        db.session.add(profile)
        db.session.commit()

    return ok({
        "todo": max(total - completed, 0),
        "completed": completed,
        "avg_score": avg_score_all,
        "latest_score": latest_score,
        "submission_rate": submission_rate,
        "avg_score_all": avg_score_all,
        "avg_score_week": avg_score_week,
        "trend": trend_items,
        "analysis": analysis
    })

