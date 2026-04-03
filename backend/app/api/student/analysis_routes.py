from .shared import *
from .shared import _rule_based_analysis, _ai_analysis, _normalize_lang, _localize_analysis


def _build_analysis_marker(assignments, submissions):
    # Use stable score-related fields to detect true data changes,
    # avoiding reliance on timestamp precision/timezone differences.
    assignment_parts = []
    for a in sorted(assignments or [], key=lambda x: x.publish_id):
        assignment_parts.append(
            f"{a.publish_id}:{a.status or ''}:{a.score if a.score is not None else ''}:{(a.completed_at or a.created_at or '')}"
        )

    submission_parts = []
    for s in sorted(submissions or [], key=lambda x: x.publish_id):
        submission_parts.append(
            "|".join(
                [
                    str(s.publish_id),
                    str(s.status or ""),
                    str(s.auto_score if s.auto_score is not None else ""),
                    str(s.teacher_score if s.teacher_score is not None else ""),
                    str(s.total_score if s.total_score is not None else ""),
                    str(s.updated_at or s.created_at or ""),
                ]
            )
        )

    return "#".join(assignment_parts) + "@@" + "#".join(submission_parts)

@bp.route("/overview", methods=["GET"])
@token_required
def overview():
    lang = _normalize_lang(request.args.get("lang") or "zh")

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

    # 学情分析应同时响应两类事件：
    # 1) 新完成作业；2) 教师批改后分数更新。
    # 仅看 completed_at 会遗漏“已完成作业被后续批改”的场景。
    completed_events = [
        a for a in assignments
        if a.status == "completed" and (a.completed_at or a.created_at)
    ]

    graded_events = []
    if pub_ids:
        graded_events = (
            ExerciseSubmission.query
            .filter(
                ExerciseSubmission.publish_id.in_(pub_ids),
                ExerciseSubmission.student_id == profile.student_id,
            )
            .all()
        )

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
    if completed_events:
        latest_completed_at = max(
            [a.completed_at or a.created_at for a in completed_events],
            default=None
        )

    latest_scored_at = None
    if graded_events:
        latest_scored_at = max(
            [
                s.updated_at or s.created_at
                for s in graded_events
                if (s.updated_at or s.created_at) and (s.status == "graded" or s.teacher_score is not None)
            ],
            default=None,
        )

    latest_signal_at = max(
        [dt for dt in [latest_completed_at, latest_scored_at] if dt],
        default=None,
    )

    cached_analysis = None
    cached_marker = ""
    if profile.analysis_json:
        try:
            cached_analysis = json.loads(profile.analysis_json)
            if isinstance(cached_analysis, dict):
                cached_marker = str(cached_analysis.get("_marker") or "")
                cached_analysis = {
                    "weak_spot": cached_analysis.get("weak_spot", ""),
                    "study_state": cached_analysis.get("study_state", ""),
                    "study_tip": cached_analysis.get("study_tip", ""),
                }
        except Exception:
            cached_analysis = None

    current_marker = _build_analysis_marker(assignments, graded_events)

    should_recompute = False
    if not cached_analysis:
        should_recompute = True
    elif cached_marker != current_marker:
        should_recompute = True
    elif latest_signal_at and (not profile.analysis_updated_at or latest_signal_at > profile.analysis_updated_at):
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

        stored_analysis = dict(analysis or {})
        stored_analysis["_marker"] = current_marker
        profile.analysis_json = json.dumps(stored_analysis, ensure_ascii=False)
        profile.analysis_updated_at = datetime.datetime.now()
        profile.analysis_latest_completed_at = latest_signal_at
        db.session.add(profile)
        db.session.commit()

    localized_analysis = _localize_analysis(analysis, lang)

    return ok({
        "todo": max(total - completed, 0),
        "completed": completed,
        "avg_score": avg_score_all,
        "latest_score": latest_score,
        "submission_rate": submission_rate,
        "avg_score_all": avg_score_all,
        "avg_score_week": avg_score_week,
        "trend": trend_items,
        "analysis": localized_analysis
    })

