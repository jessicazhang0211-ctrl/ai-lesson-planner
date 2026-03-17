import datetime
import json

from app.models.resource_assignment import ResourceAssignment
from app.models.resource_publish import ResourcePublish
from app.repositories.resource_repository import ResourceRepository


class ServiceError(Exception):
    def __init__(self, message: str, http_status: int = 400):
        super().__init__(message)
        self.message = message
        self.http_status = http_status


class ResourceService:
    def __init__(self, repo: ResourceRepository | None = None):
        self.repo = repo or ResourceRepository()

    @staticmethod
    def _loads_json(text: str | None, default):
        try:
            return json.loads(text) if text else default
        except Exception:
            return default

    @staticmethod
    def _require_user(user_id: int) -> int:
        uid = int(user_id or 0)
        if not uid:
            raise ServiceError("missing user", 401)
        return uid

    def publish_resource(self, user_id: int, data: dict) -> dict:
        uid = self._require_user(user_id)

        resource_type = (data.get("resource_type") or "").strip()
        resource_id = data.get("resource_id")
        class_id = data.get("class_id")
        student_ids = data.get("student_ids") or []
        accuracy_rule = data.get("accuracy_rule") or {}
        mode = data.get("mode") or ""

        if resource_type not in ("lesson", "exercise"):
            raise ServiceError("invalid resource_type", 400)
        if not resource_id or not class_id:
            raise ServiceError("resource_id and class_id required", 400)
        if not isinstance(student_ids, list) or not student_ids:
            raise ServiceError("student_ids required", 400)

        record = ResourcePublish(
            resource_type=resource_type,
            resource_id=int(resource_id),
            class_id=int(class_id),
            student_ids=json.dumps(student_ids, ensure_ascii=False),
            accuracy_rule=json.dumps(accuracy_rule, ensure_ascii=False),
            mode=mode,
            revoked=False,
            created_by=uid,
            created_at=datetime.datetime.now(),
        )

        assignments = []
        for sid in student_ids:
            try:
                assignments.append(ResourceAssignment(publish_id=record.id, student_id=int(sid)))
            except Exception:
                continue

        # Persist publish first so assignment foreign key can reference generated id.
        self.repo.create_publish(record)

        if assignments:
            for a in assignments:
                a.publish_id = record.id
            self.repo.create_assignments(assignments)

        return record.to_dict()

    def list_published(self, user_id: int, class_id: str | None) -> list[dict]:
        uid = self._require_user(user_id)

        class_id_int = None
        if class_id:
            try:
                class_id_int = int(class_id)
            except ValueError:
                raise ServiceError("invalid class_id", 400)

        records = self.repo.list_published(uid, class_id_int)

        lesson_ids = [r.resource_id for r in records if r.resource_type == "lesson"]
        exercise_ids = [r.resource_id for r in records if r.resource_type == "exercise"]
        class_ids = [r.class_id for r in records]

        lessons = self.repo.get_lessons_map(lesson_ids)
        exercises = self.repo.get_exercises_map(exercise_ids)
        classes = self.repo.get_classes_map(class_ids)

        result = []
        for r in records:
            item = r.to_dict()
            if r.resource_type == "lesson":
                item["title"] = lessons.get(r.resource_id).title if lessons.get(r.resource_id) else ""
            else:
                item["title"] = exercises.get(r.resource_id).title if exercises.get(r.resource_id) else ""
            item["class_name"] = classes.get(r.class_id).name if classes.get(r.class_id) else ""
            result.append(item)
        return result

    def list_review(self, user_id: int, class_id: str | None, status: str) -> list[dict]:
        uid = self._require_user(user_id)

        class_id_int = None
        if class_id:
            try:
                class_id_int = int(class_id)
            except ValueError:
                raise ServiceError("invalid class_id", 400)

        pubs = self.repo.list_publishes(uid, class_id_int)
        pub_ids = [p.id for p in pubs]
        if not pub_ids:
            return []

        submissions = self.repo.list_submissions_by_publish_ids(pub_ids, status)
        students = self.repo.get_students_map([s.student_id for s in submissions])
        classes = self.repo.get_classes_map(list({p.class_id for p in pubs}))
        exercises = self.repo.get_exercises_map([p.resource_id for p in pubs if p.resource_type == "exercise"])

        pub_map = {p.id: p for p in pubs}
        result = []
        for s in submissions:
            pub = pub_map.get(s.publish_id)
            if not pub:
                continue
            ex = exercises.get(pub.resource_id)
            student = students.get(s.student_id)
            result.append(
                {
                    "submission_id": s.id,
                    "publish_id": s.publish_id,
                    "class_id": pub.class_id,
                    "class_name": classes.get(pub.class_id).name if classes.get(pub.class_id) else "",
                    "title": ex.title if ex else "",
                    "auto_score": s.auto_score,
                    "student_name": student.name if student else "",
                    "status": s.status,
                    "created_at": s.created_at.strftime("%Y-%m-%d %H:%M:%S") if s.created_at else "",
                }
            )
        return result

    def review_detail(self, user_id: int, submission_id: int) -> dict:
        uid = self._require_user(user_id)

        submission = self.repo.find_submission(submission_id)
        if not submission:
            raise ServiceError("submission not found", 404)

        pub = self.repo.find_publish(submission.publish_id)
        if not pub or pub.created_by != uid:
            raise ServiceError("not allowed", 403)

        exercise = self.repo.find_exercise(pub.resource_id)
        if not exercise or not exercise.content_json:
            raise ServiceError("exercise format not supported", 400)

        try:
            structured = json.loads(exercise.content_json)
        except Exception:
            raise ServiceError("invalid exercise format", 400)

        answers = self._loads_json(submission.answers, {})
        teacher_detail = self._loads_json(submission.teacher_detail, {})

        questions = []
        for q in structured.get("questions", []):
            q2 = dict(q)
            qid = q.get("id")
            qtype = (q.get("type") or "").lower()
            q2["student_answer"] = answers.get(qid)
            q2["is_subjective"] = qtype in ("short", "essay")
            q2["teacher_score"] = (teacher_detail.get(qid) or {}).get("score") if qid else None
            questions.append(q2)

        return {
            "submission_id": submission.id,
            "publish_id": pub.id,
            "title": exercise.title,
            "auto_score": submission.auto_score,
            "teacher_score": submission.teacher_score,
            "total_score": submission.total_score,
            "teacher_comment": submission.teacher_comment or "",
            "status": submission.status,
            "questions": questions,
        }

    def review_history(self, user_id: int, class_id: str | None, title_kw: str, student_kw: str) -> list[dict]:
        uid = self._require_user(user_id)

        class_id_int = None
        if class_id:
            try:
                class_id_int = int(class_id)
            except ValueError:
                raise ServiceError("invalid class_id", 400)

        pubs = self.repo.list_publishes(uid, class_id_int)
        pub_ids = [p.id for p in pubs]
        if not pub_ids:
            return []

        submissions = self.repo.list_graded_submissions(pub_ids)
        classes = self.repo.get_classes_map(list({p.class_id for p in pubs}))
        exercises = self.repo.get_exercises_map([p.resource_id for p in pubs if p.resource_type == "exercise"])
        students = self.repo.get_students_map([s.student_id for s in submissions])

        pub_map = {p.id: p for p in pubs}
        result = []
        for s in submissions:
            pub = pub_map.get(s.publish_id)
            if not pub:
                continue
            ex = exercises.get(pub.resource_id)
            student = students.get(s.student_id)

            if title_kw and ex and title_kw not in (ex.title or ""):
                continue
            if student_kw and student and student_kw not in (student.name or ""):
                continue

            result.append(
                {
                    "submission_id": s.id,
                    "publish_id": s.publish_id,
                    "class_id": pub.class_id,
                    "class_name": classes.get(pub.class_id).name if classes.get(pub.class_id) else "",
                    "title": ex.title if ex else "",
                    "auto_score": s.auto_score,
                    "teacher_score": s.teacher_score,
                    "total_score": s.total_score,
                    "student_name": student.name if student else "",
                    "teacher_comment": s.teacher_comment or "",
                    "status": s.status,
                    "created_at": s.updated_at.strftime("%Y-%m-%d %H:%M:%S") if s.updated_at else "",
                }
            )
        return result

    def review_score(self, user_id: int, submission_id: int, data: dict) -> dict:
        uid = self._require_user(user_id)

        submission = self.repo.find_submission(submission_id)
        if not submission:
            raise ServiceError("submission not found", 404)

        pub = self.repo.find_publish(submission.publish_id)
        if not pub or pub.created_by != uid:
            raise ServiceError("not allowed", 403)

        scores = data.get("scores") or {}
        teacher_comment = data.get("teacher_comment") or ""

        exercise = self.repo.find_exercise(pub.resource_id)
        if not exercise or not exercise.content_json:
            raise ServiceError("exercise format not supported", 400)

        try:
            structured = json.loads(exercise.content_json)
        except Exception:
            raise ServiceError("invalid exercise format", 400)

        max_scores = {}
        subjective_ids = set()
        for q in structured.get("questions", []):
            qid = q.get("id")
            if not qid:
                continue
            qtype = (q.get("type") or "").lower()
            if qtype in ("short", "essay"):
                subjective_ids.add(qid)
                try:
                    max_scores[qid] = int(q.get("score") or 0)
                except Exception:
                    max_scores[qid] = 0

        teacher_detail = {}
        teacher_score = 0
        for qid, raw_score in scores.items():
            if qid not in subjective_ids:
                continue
            try:
                value = int(raw_score)
            except Exception:
                raise ServiceError("invalid teacher_score", 400)
            max_s = max_scores.get(qid, 0)
            if value < 0 or value > max_s:
                raise ServiceError("invalid teacher_score", 400)
            teacher_detail[qid] = {"score": value}
            teacher_score += value

        submission.teacher_score = teacher_score
        submission.teacher_detail = json.dumps(teacher_detail, ensure_ascii=False)
        submission.teacher_comment = teacher_comment
        submission.total_score = (submission.auto_score or 0) + teacher_score
        submission.status = "graded"
        self.repo.commit()

        assignment = self.repo.find_assignment(submission.publish_id, submission.student_id)
        if assignment:
            assignment.score = submission.total_score
            assignment.status = "completed"
            self.repo.commit()

        return submission.to_dict()

    def revoke_published(self, user_id: int, pub_id: int) -> dict:
        uid = self._require_user(user_id)

        record = self.repo.find_publish(pub_id)
        if not record or record.created_by != uid:
            raise ServiceError("record not found", 404)

        self.repo.revoke_publish(record)
        return record.to_dict()

    def resource_stats(self, user_id: int, resource_type: str, resource_id: int, class_id: str | None) -> dict:
        if resource_type not in ("lesson", "exercise"):
            raise ServiceError("invalid resource_type", 400)

        uid = self._require_user(user_id)

        class_id_int = None
        if class_id:
            try:
                class_id_int = int(class_id)
            except ValueError:
                raise ServiceError("invalid class_id", 400)

        pubs = [
            p
            for p in self.repo.list_publishes(uid, class_id_int)
            if p.resource_type == resource_type and p.resource_id == resource_id
        ]

        pub_ids = [p.id for p in pubs]
        if not pub_ids:
            return {"overall": {"assigned": 0, "completed": 0, "rate": 0}, "classes": [], "questions": [], "trend": []}

        assignments = self.repo.list_assignments_by_publish_ids(pub_ids)

        class_map = {}
        pub_to_class = {}
        for p in pubs:
            pub_to_class[p.id] = p.class_id
            if p.class_id not in class_map:
                class_map[p.class_id] = {"assigned": 0, "completed": 0, "last_published_at": p.created_at}
            if p.created_at and p.created_at > class_map[p.class_id]["last_published_at"]:
                class_map[p.class_id]["last_published_at"] = p.created_at

        for a in assignments:
            c_id = pub_to_class.get(a.publish_id)
            if not c_id:
                continue
            bucket = class_map.get(c_id)
            if not bucket:
                continue
            bucket["assigned"] += 1
            if a.status == "completed":
                bucket["completed"] += 1

        total_assigned = sum(v["assigned"] for v in class_map.values())
        total_completed = sum(v["completed"] for v in class_map.values())
        rate = int(round((total_completed / total_assigned) * 100)) if total_assigned else 0

        class_ids = list(class_map.keys())
        classes = self.repo.get_classes_map(class_ids)

        class_list = []
        for c_id, value in class_map.items():
            assigned = value["assigned"]
            completed = value["completed"]
            class_list.append(
                {
                    "class_id": c_id,
                    "class_name": classes.get(c_id).name if classes.get(c_id) else "",
                    "assigned": assigned,
                    "completed": completed,
                    "rate": int(round((completed / assigned) * 100)) if assigned else 0,
                    "last_published_at": value["last_published_at"].strftime("%Y-%m-%d %H:%M:%S") if value["last_published_at"] else "",
                }
            )

        questions_stats = []
        trend = []
        if resource_type == "exercise":
            exercise = self.repo.find_exercise(resource_id)
            if exercise and exercise.content_json:
                structured = self._loads_json(exercise.content_json, {})
                questions = structured.get("questions", [])

                submissions = self.repo.list_graded_submissions(pub_ids)

                for s in list(reversed(submissions[:10])):
                    dt = s.updated_at or s.created_at
                    trend.append({"label": dt.strftime("%m-%d") if dt else "", "score": s.total_score})

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
                    auto_result = self._loads_json(s.auto_result, {})
                    teacher_detail = self._loads_json(s.teacher_detail, {})

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
                    avg_score = round(totals[qid] / counts[qid], 2) if counts[qid] else None
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

        return {
            "overall": {"assigned": total_assigned, "completed": total_completed, "rate": rate},
            "classes": class_list,
            "questions": questions_stats,
            "trend": trend,
        }
