import json
import csv
import os
from io import StringIO

from flask import g, request

from app.services.ai_service import ai_service
from app.models.classroom import Classroom
from app.models.exercise import Exercise
from app.models.exercise_submission import ExerciseSubmission
from app.models.assignment_analysis import AssignmentAnalysis
from app.models.resource_assignment import ResourceAssignment
from app.models.resource_publish import ResourcePublish
from app.services.knowledge_base_service import list_knowledge_items, save_knowledge_items
from app.utils.auth import token_required
from app.utils.response import err, ok

from .blueprint import bp


_PUBLISH_AI_SUMMARY_CACHE = {}


def _normalize_lang(lang):
    return "en" if str(lang or "zh").lower().startswith("en") else "zh"


def _safe_json_list(raw):
    try:
        value = json.loads(raw or "")
        return value if isinstance(value, list) else []
    except Exception:
        return []


def _safe_int(value, default=None):
    try:
        return int(value)
    except Exception:
        return default


def _to_text(raw_bytes: bytes) -> str:
    for enc in ("utf-8", "utf-8-sig", "gbk"):
        try:
            return raw_bytes.decode(enc)
        except Exception:
            continue
    return raw_bytes.decode("utf-8", errors="ignore")


def _parse_knowledge_upload(filename: str, text: str, default_topic: str, default_tags, default_class_id=None):
    ext = (os.path.splitext(filename or "")[1] or "").lower()
    filename_topic = (os.path.splitext(os.path.basename(filename or ""))[0] or "").strip()
    fallback_topic = (default_topic or filename_topic or "导入知识").strip()
    base = {
        "topic": fallback_topic,
        "tags": default_tags,
        "class_id": default_class_id,
        "source": "import",
    }

    if ext == ".json":
        try:
            payload = json.loads(text or "")
        except Exception:
            payload = None

        if isinstance(payload, dict):
            payload = payload.get("items") if isinstance(payload.get("items"), list) else [payload]

        items = []
        if isinstance(payload, list):
            for row in payload:
                if not isinstance(row, dict):
                    continue
                item = dict(base)
                item["topic"] = str(row.get("topic") or base["topic"] or "").strip()
                item["title"] = str(row.get("title") or "").strip()
                item["content"] = str(row.get("content") or row.get("text") or "").strip()
                item["tags"] = row.get("tags") if row.get("tags") is not None else base["tags"]
                item["class_id"] = _safe_int(row.get("class_id"), default_class_id)
                items.append(item)
        return items

    if ext == ".csv":
        rows = []
        reader = csv.DictReader(StringIO(text or ""))
        for row in reader:
            item = dict(base)
            item["topic"] = str(row.get("topic") or base["topic"] or "").strip()
            item["title"] = str(row.get("title") or "").strip()
            item["content"] = str(row.get("content") or row.get("text") or "").strip()
            item["tags"] = row.get("tags") if row.get("tags") is not None else base["tags"]
            item["class_id"] = _safe_int(row.get("class_id"), default_class_id)
            rows.append(item)
        return rows

    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    return [
        {
            **base,
            "title": "",
            "content": ln,
        }
        for ln in lines
    ]


@bp.route("/knowledge-base", methods=["GET"])
@token_required
def knowledge_base_overview():
    user_id = int(getattr(g, "current_user_id", 0) or 0)
    if not user_id:
        return err("missing user", http_status=401)

    class_id = request.args.get("class_id")
    selected_topic = (request.args.get("topic") or "").strip()
    try:
        timeline_limit = max(1, min(int(request.args.get("limit") or 50), 200))
    except Exception:
        timeline_limit = 50

    rows_q = AssignmentAnalysis.query.filter_by(created_by=user_id)
    if class_id:
        try:
            class_id = int(class_id)
            rows_q = rows_q.filter_by(class_id=class_id)
        except ValueError:
            return err("invalid class_id", http_status=400)

    rows = rows_q.order_by(AssignmentAnalysis.updated_at.desc()).limit(1000).all()

    topic_buckets = {}
    for row in rows:
        key = (row.topic or row.title or "未分类课题").strip() or "未分类课题"
        bucket = topic_buckets.get(key)
        if bucket is None:
            bucket = {
                "topic": key,
                "count": 0,
                "latest_at": row.updated_at,
                "avg_completion_rate": 0.0,
                "_completion_sum": 0.0,
                "_completion_count": 0,
            }
            topic_buckets[key] = bucket

        bucket["count"] += 1
        if row.updated_at and (bucket["latest_at"] is None or row.updated_at > bucket["latest_at"]):
            bucket["latest_at"] = row.updated_at
        if row.completion_rate is not None:
            bucket["_completion_sum"] += float(row.completion_rate)
            bucket["_completion_count"] += 1

    topics = []
    for bucket in topic_buckets.values():
        ccount = bucket.pop("_completion_count", 0)
        csum = bucket.pop("_completion_sum", 0.0)
        bucket["avg_completion_rate"] = round((csum / ccount), 1) if ccount else None
        bucket["latest_at"] = bucket["latest_at"].strftime("%Y-%m-%d %H:%M:%S") if bucket.get("latest_at") else ""
        topics.append(bucket)
    topics.sort(key=lambda x: (x.get("count") or 0, x.get("latest_at") or ""), reverse=True)

    filtered_rows = rows
    if selected_topic:
        st = selected_topic.lower()
        filtered_rows = [
            r
            for r in rows
            if st in str((r.topic or "")).lower() or st in str((r.title or "")).lower()
        ]

    filtered_rows = filtered_rows[:timeline_limit]

    misconception_counter = {}
    wrong_question_counter = {}
    wrong_question_examples = {}
    timeline = []
    for row in filtered_rows:
        weak_types = _safe_json_list(row.weak_question_types_json)
        summary = str(row.summary_text or "").strip()
        analysis_obj = {}
        try:
            analysis_obj = json.loads(row.analysis_json or "{}")
        except Exception:
            analysis_obj = {}
        wrong_questions = analysis_obj.get("wrong_questions") if isinstance(analysis_obj, dict) else []
        if not isinstance(wrong_questions, list):
            wrong_questions = []

        misconceptions = _safe_json_list(row.common_misconceptions_json)
        if not misconceptions:
            misconceptions = []
        # Backfill older truncated misconception strings from stored wrong-question details.
        recovered_misconceptions = []
        for w in wrong_questions:
            if not isinstance(w, dict):
                continue
            stem = str(w.get("stem") or "").strip()
            if stem:
                recovered_misconceptions.append(stem)
        if recovered_misconceptions:
            has_truncated = any(
                isinstance(x, str) and len(x.strip()) >= 55 and ("..." not in x)
                for x in misconceptions
            )
            if (not misconceptions) or has_truncated:
                misconceptions = recovered_misconceptions[:3]

        for m in misconceptions:
            text = str(m or "").strip()
            if not text:
                continue
            misconception_counter[text] = misconception_counter.get(text, 0) + 1

        timeline_wrong_questions = []
        for w in wrong_questions:
            if not isinstance(w, dict):
                continue
            stem = str(w.get("stem") or "").strip()
            if not stem:
                continue
            stem_key = stem[:120]
            wrong_question_counter[stem_key] = wrong_question_counter.get(stem_key, 0) + 1
            if stem_key not in wrong_question_examples:
                wrong_question_examples[stem_key] = {
                    "stem": stem,
                    "type": str(w.get("type") or ""),
                    "analysis": str(w.get("analysis") or ""),
                }
            timeline_wrong_questions.append(
                {
                    "id": w.get("id"),
                    "type": w.get("type") or "",
                    "stem": stem,
                    "analysis": str(w.get("analysis") or ""),
                }
            )

        timeline.append(
            {
                "submission_id": row.submission_id,
                "publish_id": row.publish_id,
                "class_id": row.class_id,
                "topic": (row.topic or row.title or "").strip(),
                "title": row.title or "",
                "score": row.score,
                "max_score": row.max_score,
                "completion_rate": row.completion_rate,
                "weak_question_types": weak_types,
                "common_misconceptions": misconceptions,
                "wrong_questions": timeline_wrong_questions[:5],
                "summary": summary,
                "updated_at": row.updated_at.strftime("%Y-%m-%d %H:%M:%S") if row.updated_at else "",
            }
        )

    misconception_heat = [
        {"name": k, "count": v}
        for k, v in sorted(misconception_counter.items(), key=lambda kv: kv[1], reverse=True)
    ]

    wrong_question_heat = []
    for stem, count in sorted(wrong_question_counter.items(), key=lambda kv: kv[1], reverse=True):
        ex = wrong_question_examples.get(stem) or {}
        wrong_question_heat.append(
            {
                "stem": stem,
                "count": count,
                "type": ex.get("type") or "",
                "analysis": ex.get("analysis") or "",
            }
        )

    return ok(
        {
            "topics": topics,
            "selected_topic": selected_topic,
            "timeline": timeline,
            "misconception_heat": misconception_heat,
            "wrong_question_heat": wrong_question_heat[:50],
            "total_records": len(rows),
            "filtered_records": len(filtered_rows),
        }
    )


@bp.route("/knowledge-items", methods=["GET"])
@token_required
def knowledge_items_list():
    user_id = int(getattr(g, "current_user_id", 0) or 0)
    if not user_id:
        return err("missing user", http_status=401)

    class_id_raw = request.args.get("class_id")
    class_id = _safe_int(class_id_raw, None) if str(class_id_raw or "").strip() else None
    topic = (request.args.get("topic") or "").strip()
    limit = _safe_int(request.args.get("limit"), 100) or 100
    rows = list_knowledge_items(created_by=user_id, class_id=class_id, topic=topic, limit=limit)
    return ok({"items": rows, "total": len(rows)})


@bp.route("/knowledge-items/import", methods=["POST", "OPTIONS"])
@token_required
def knowledge_items_import():
    if request.method == "OPTIONS":
        return ok({"msg": "CORS preflight ok"})

    user_id = int(getattr(g, "current_user_id", 0) or 0)
    if not user_id:
        return err("missing user", http_status=401)

    is_multipart = request.content_type and "multipart/form-data" in request.content_type.lower()
    payload = request.form.to_dict(flat=True) if is_multipart else (request.get_json(silent=True) or {})

    default_topic = str(payload.get("topic") or "").strip()
    default_class_id = _safe_int(payload.get("class_id"), None)
    default_tags = str(payload.get("tags") or "").replace("，", ",")
    default_tags = [x.strip() for x in default_tags.split(",") if x.strip()]

    items = []
    if is_multipart and request.files.get("file"):
        upload = request.files.get("file")
        raw = upload.read() if upload else b""
        text = _to_text(raw) if raw else ""
        items = _parse_knowledge_upload(
            filename=getattr(upload, "filename", "") or "",
            text=text,
            default_topic=default_topic,
            default_tags=default_tags,
            default_class_id=default_class_id,
        )
    else:
        manual_content = str(payload.get("content") or "").strip()
        manual_title = str(payload.get("title") or "").strip()
        payload_items = payload.get("items") if isinstance(payload, dict) else None
        if isinstance(payload_items, list):
            items = payload_items
        elif manual_content:
            items = [
                {
                    "topic": default_topic,
                    "title": manual_title,
                    "content": manual_content,
                    "tags": default_tags,
                    "class_id": default_class_id,
                    "source": "manual",
                }
            ]

    saved = save_knowledge_items(
        created_by=user_id,
        items=items,
        default_class_id=default_class_id,
        source="import",
    )
    if saved <= 0:
        return err("no valid knowledge rows to import", http_status=400)

    return ok({"saved": saved})


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
    if not exercise:
        return err("exercise not found", http_status=404)

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
