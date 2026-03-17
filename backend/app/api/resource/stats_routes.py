import json

from flask import g, request

from app.models.classroom import Classroom
from app.models.exercise import Exercise
from app.models.exercise_submission import ExerciseSubmission
from app.models.resource_assignment import ResourceAssignment
from app.models.resource_publish import ResourcePublish
from app.utils.auth import token_required
from app.utils.response import err, ok

from .blueprint import bp


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
