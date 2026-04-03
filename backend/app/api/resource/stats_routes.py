import json

from flask import g, request

from app.services.ai_service import ai_service
from app.models.classroom import Classroom
from app.models.exercise import Exercise
from app.models.exercise_submission import ExerciseSubmission
from app.models.resource_assignment import ResourceAssignment
from app.models.resource_publish import ResourcePublish
from app.utils.auth import token_required
from app.utils.response import err, ok

from .blueprint import bp


_PUBLISH_AI_SUMMARY_CACHE = {}


def _normalize_lang(lang):
    return "en" if str(lang or "zh").lower().startswith("en") else "zh"


def _event_marker(assignments, submissions):
    completed = [a for a in assignments if (a.status == "completed")]
    graded = [s for s in submissions if (s.status == "graded")]

    latest_completed = None
    if completed:
        latest_completed = max([(a.completed_at or a.created_at) for a in completed if (a.completed_at or a.created_at)], default=None)

    latest_graded = None
    if graded:
        latest_graded = max([(s.updated_at or s.created_at) for s in graded if (s.updated_at or s.created_at)], default=None)

    completed_ts = latest_completed.strftime("%Y-%m-%d %H:%M:%S") if latest_completed else ""
    graded_ts = latest_graded.strftime("%Y-%m-%d %H:%M:%S") if latest_graded else ""
    return f"c:{len(completed)}:{completed_ts}|g:{len(graded)}:{graded_ts}"


def _build_local_publish_ai_summary(exercise, assignments, submissions, lang="zh"):
    lang = _normalize_lang(lang)
    try:
        structured = json.loads(exercise.content_json or "{}")
    except Exception:
        structured = {}

    questions = structured.get("questions") or []
    total_questions = len(questions)
    subjective_count = 0
    objective_count = 0
    for q in questions:
        qtype = str((q or {}).get("type") or "").lower()
        if qtype in ("short", "essay"):
            subjective_count += 1
        else:
            objective_count += 1

    assigned = len(assignments)
    completed = len([a for a in assignments if a.status == "completed"])
    completion_rate = round((completed / assigned) * 100, 1) if assigned else 0

    graded_subs = [s for s in submissions if s.status == "graded"]
    avg_total = None
    if graded_subs:
        vals = [int(s.total_score or 0) for s in graded_subs]
        avg_total = round(sum(vals) / len(vals), 1) if vals else None

    if lang == "en":
        lines = [
            "1. Key Points and Challenges",
            f"- Question count: {total_questions} (objective {objective_count}, subjective {subjective_count})",
            f"- Topic: {exercise.title or 'This assignment'}",
            "",
            "2. Class Performance Summary",
            f"- Assigned students: {assigned}",
            f"- Completed: {completed}",
            f"- Completion rate: {completion_rate}%",
            f"- Graded submissions: {len(graded_subs)}",
            f"- Average total score: {avg_total if avg_total is not None else '-'}",
            "",
            "3. Teaching Suggestions",
            "- Remind non-completers and provide a short catch-up task.",
            "- Re-teach high-error concepts and assign 3-5 targeted follow-up items.",
        ]
    else:
        lines = [
            "1. 重难点",
            f"- 题量：{total_questions}（客观题 {objective_count}，主观题 {subjective_count}）",
            f"- 主题：{exercise.title or '本次作业'}",
            "",
            "2. 班级作业情况总结",
            f"- 已发布人数：{assigned}",
            f"- 已完成人数：{completed}",
            f"- 完成率：{completion_rate}%",
            f"- 已批改份数：{len(graded_subs)}",
            f"- 平均总分：{avg_total if avg_total is not None else '-'}",
            "",
            "3. 教学建议",
            "- 对未完成学生进行提醒并安排补做任务。",
            "- 针对高错题知识点进行再讲解并布置3-5道巩固题。",
        ]
    return "\n".join(lines)


@bp.route("/resource/<string:resource_type>/<int:resource_id>/stats", methods=["GET"])
@token_required
def resource_stats(resource_type: str, resource_id: int):
    if resource_type not in ("lesson", "exercise"):
        return err("invalid resource_type", http_status=400)

    user_id = int(getattr(g, "current_user_id", 0) or 0)
    if not user_id:
        return err("missing user", http_status=401)

    class_id = request.args.get("class_id")
    pubs_q = ResourcePublish.query.filter_by(
        created_by=user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        revoked=False,
    )
    if class_id:
        try:
            class_id = int(class_id)
            pubs_q = pubs_q.filter_by(class_id=class_id)
        except ValueError:
            return err("invalid class_id", http_status=400)

    pubs = pubs_q.all()

    pub_ids = [p.id for p in pubs]
    if not pub_ids:
        return ok(
            {
                "overall": {"assigned": 0, "completed": 0, "rate": 0},
                "classes": [],
                "questions": [],
                "trend": [],
            }
        )

    assignments = ResourceAssignment.query.filter(ResourceAssignment.publish_id.in_(pub_ids)).all()

    class_map = {}
    pub_to_class = {}
    for p in pubs:
        pub_to_class[p.id] = p.class_id
        if p.class_id not in class_map:
            class_map[p.class_id] = {
                "assigned": 0,
                "completed": 0,
                "last_published_at": p.created_at,
            }
        if p.created_at and p.created_at > class_map[p.class_id]["last_published_at"]:
            class_map[p.class_id]["last_published_at"] = p.created_at

    for a in assignments:
        mapped_class_id = pub_to_class.get(a.publish_id)
        if not mapped_class_id:
            continue
        bucket = class_map.get(mapped_class_id)
        if not bucket:
            continue
        bucket["assigned"] += 1
        if a.status == "completed":
            bucket["completed"] += 1

    total_assigned = sum(v["assigned"] for v in class_map.values())
    total_completed = sum(v["completed"] for v in class_map.values())
    rate = int(round((total_completed / total_assigned) * 100)) if total_assigned else 0

    class_ids = list(class_map.keys())
    classes = {c.id: c for c in Classroom.query.filter(Classroom.id.in_(class_ids)).all()} if class_ids else {}

    class_list = []
    for cid, values in class_map.items():
        assigned = values["assigned"]
        completed = values["completed"]
        class_list.append(
            {
                "class_id": cid,
                "class_name": classes.get(cid).name if classes.get(cid) else "",
                "assigned": assigned,
                "completed": completed,
                "rate": int(round((completed / assigned) * 100)) if assigned else 0,
                "last_published_at": values["last_published_at"].strftime("%Y-%m-%d %H:%M:%S")
                if values["last_published_at"]
                else "",
            }
        )

    questions_stats = []
    trend = []
    if resource_type == "exercise":
        exercise = Exercise.query.get(resource_id)
        if exercise and exercise.content_json:
            try:
                structured = json.loads(exercise.content_json)
            except Exception:
                structured = {}
            questions = structured.get("questions", [])

            submissions = ExerciseSubmission.query.filter(
                ExerciseSubmission.publish_id.in_(pub_ids),
                ExerciseSubmission.status == "graded",
            ).order_by(ExerciseSubmission.updated_at.desc()).all()

            for s in list(reversed(submissions[:10])):
                dt = s.updated_at or s.created_at
                label = dt.strftime("%m-%d") if dt else ""
                trend.append({"label": label, "score": s.total_score})

            totals = {}
            wrongs = {}
            counts = {}
            max_scores = {}
            qtypes = {}
            stems = {}
            analyses = {}

            for q in questions:
                qid = q.get("id")
                if not qid:
                    continue
                try:
                    max_scores[qid] = int(q.get("score") or 0)
                except Exception:
                    max_scores[qid] = 0
                qtypes[qid] = q.get("type") or ""
                stems[qid] = q.get("stem") or ""
                analyses[qid] = q.get("analysis") or ""
                totals[qid] = 0
                wrongs[qid] = 0
                counts[qid] = 0

            for s in submissions:
                try:
                    auto_result = json.loads(s.auto_result or "{}")
                except Exception:
                    auto_result = {}
                try:
                    teacher_detail = json.loads(s.teacher_detail or "{}")
                except Exception:
                    teacher_detail = {}

                for qid in counts.keys():
                    qtype = (qtypes.get(qid) or "").lower()
                    max_s = max_scores.get(qid, 0)
                    score = None
                    if qtype in ("short", "essay"):
                        score = (teacher_detail.get(qid) or {}).get("score")
                        if score is None:
                            continue
                        wrong = score < max_s
                    else:
                        result = auto_result.get(qid)
                        if result is None:
                            continue
                        score = max_s if result == "correct" else 0
                        wrong = result == "wrong"
                    totals[qid] += score
                    counts[qid] += 1
                    if wrong:
                        wrongs[qid] += 1

            for qid in counts.keys():
                if counts[qid] == 0:
                    avg_score = None
                else:
                    avg_score = round(totals[qid] / counts[qid], 2)
                questions_stats.append(
                    {
                        "id": qid,
                        "stem": stems.get(qid, ""),
                        "type": qtypes.get(qid, ""),
                        "analysis": analyses.get(qid, ""),
                        "max_score": max_scores.get(qid, 0),
                        "avg_score": avg_score,
                        "wrong_count": wrongs.get(qid, 0),
                        "answer_count": counts.get(qid, 0),
                    }
                )

    return ok(
        {
            "overall": {"assigned": total_assigned, "completed": total_completed, "rate": rate},
            "classes": class_list,
            "questions": questions_stats,
            "trend": trend,
        }
    )


@bp.route("/publish/<int:pub_id>/ai-summary", methods=["GET"])
@token_required
def publish_ai_summary(pub_id: int):
    user_id = int(getattr(g, "current_user_id", 0) or 0)
    if not user_id:
        return err("missing user", http_status=401)

    lang = _normalize_lang(request.args.get("lang") or "zh")

    pub = ResourcePublish.query.get(pub_id)
    if not pub or pub.revoked:
        return err("publish not found", http_status=404)
    if int(pub.created_by or 0) != user_id:
        return err("not allowed", http_status=403)
    if pub.resource_type != "exercise":
        return err("ai summary only supported for exercise", http_status=400)

    exercise = Exercise.query.get(pub.resource_id)
    if not exercise or not exercise.content_json:
        return err("exercise format not supported", http_status=400)

    assignments = ResourceAssignment.query.filter_by(publish_id=pub.id).all()
    submissions = ExerciseSubmission.query.filter_by(publish_id=pub.id).all()
    marker = _event_marker(assignments, submissions)
    cache_key = f"{pub.id}:{lang}"
    cached = _PUBLISH_AI_SUMMARY_CACHE.get(cache_key)
    if cached and cached.get("marker") == marker:
        return ok({"summary": cached.get("summary", ""), "source": cached.get("source", "cache"), "marker": marker})

    local_summary = _build_local_publish_ai_summary(exercise, assignments, submissions, lang)

    try:
        if lang == "en":
            prompt = (
                "You are a primary-school teaching assistant. Based on this published assignment's class-level data, "
                "write concise and actionable insights.\n"
                "Use exactly three sections:\n"
                "1) Key Points and Challenges\n"
                "2) Class Performance Summary\n"
                "3) Teaching Suggestions (max 3)\n"
                "Language: English.\n\n"
                f"Title: {exercise.title or ''}\n"
                f"Assignments count: {len(assignments)}\n"
                f"Submissions count: {len(submissions)}\n"
                f"Exercise JSON: {exercise.content_json}\n"
            )
        else:
            prompt = (
                "你是一名小学教研助理。请基于已发布作业的班级数据输出简洁、可执行的分析。\n"
                "固定三部分：\n"
                "1) 重难点\n"
                "2) 班级作业情况总结\n"
                "3) 教学建议（最多3条）\n"
                "语言：中文。\n\n"
                f"标题：{exercise.title or ''}\n"
                f"发布人数：{len(assignments)}\n"
                f"提交记录数：{len(submissions)}\n"
                f"习题JSON：{exercise.content_json}\n"
            )
        ai_text = ai_service.generate_text(prompt)
        summary = (ai_text or "").strip() or local_summary
        source = "gemini"
    except Exception:
        summary = local_summary
        source = "fallback"

    _PUBLISH_AI_SUMMARY_CACHE[cache_key] = {"marker": marker, "summary": summary, "source": source}
    return ok({"summary": summary, "source": source, "marker": marker})
