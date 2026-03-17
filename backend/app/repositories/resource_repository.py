import datetime

from app.models.classroom import Classroom, Student
from app.models.exercise import Exercise
from app.models.exercise_submission import ExerciseSubmission
from app.models.lesson import Lesson
from app.models.resource_assignment import ResourceAssignment
from app.models.resource_publish import ResourcePublish


class ResourceRepository:
    @staticmethod
    def create_publish(record: ResourcePublish) -> None:
        from app.extensions import db

        db.session.add(record)
        db.session.commit()

    @staticmethod
    def create_assignments(assignments: list[ResourceAssignment]) -> None:
        if not assignments:
            return
        from app.extensions import db

        db.session.add_all(assignments)
        db.session.commit()

    @staticmethod
    def list_published(created_by: int, class_id: int | None = None) -> list[ResourcePublish]:
        q = ResourcePublish.query.filter_by(created_by=created_by, revoked=False)
        if class_id:
            q = q.filter_by(class_id=class_id)
        return q.order_by(ResourcePublish.created_at.desc()).limit(10 if class_id else 50).all()

    @staticmethod
    def list_publishes(created_by: int, class_id: int | None = None) -> list[ResourcePublish]:
        q = ResourcePublish.query.filter_by(created_by=created_by, revoked=False)
        if class_id:
            q = q.filter_by(class_id=class_id)
        return q.all()

    @staticmethod
    def find_submission(submission_id: int) -> ExerciseSubmission | None:
        return ExerciseSubmission.query.get(submission_id)

    @staticmethod
    def find_publish(pub_id: int) -> ResourcePublish | None:
        return ResourcePublish.query.get(pub_id)

    @staticmethod
    def find_exercise(exercise_id: int) -> Exercise | None:
        return Exercise.query.get(exercise_id)

    @staticmethod
    def get_lessons_map(ids: list[int]) -> dict[int, Lesson]:
        if not ids:
            return {}
        return {l.id: l for l in Lesson.query.filter(Lesson.id.in_(ids)).all()}

    @staticmethod
    def get_exercises_map(ids: list[int]) -> dict[int, Exercise]:
        if not ids:
            return {}
        return {e.id: e for e in Exercise.query.filter(Exercise.id.in_(ids)).all()}

    @staticmethod
    def get_classes_map(ids: list[int]) -> dict[int, Classroom]:
        if not ids:
            return {}
        return {c.id: c for c in Classroom.query.filter(Classroom.id.in_(ids)).all()}

    @staticmethod
    def get_students_map(ids: list[int]) -> dict[int, Student]:
        if not ids:
            return {}
        return {s.id: s for s in Student.query.filter(Student.id.in_(ids)).all()}

    @staticmethod
    def list_submissions_by_publish_ids(pub_ids: list[int], status: str | None = None) -> list[ExerciseSubmission]:
        if not pub_ids:
            return []
        q = ExerciseSubmission.query.filter(ExerciseSubmission.publish_id.in_(pub_ids))
        if status:
            q = q.filter(ExerciseSubmission.status == status)
        return q.all()

    @staticmethod
    def list_graded_submissions(pub_ids: list[int]) -> list[ExerciseSubmission]:
        if not pub_ids:
            return []
        return (
            ExerciseSubmission.query
            .filter(ExerciseSubmission.publish_id.in_(pub_ids), ExerciseSubmission.status == "graded")
            .order_by(ExerciseSubmission.updated_at.desc())
            .all()
        )

    @staticmethod
    def list_assignments_by_publish_ids(pub_ids: list[int]) -> list[ResourceAssignment]:
        if not pub_ids:
            return []
        return ResourceAssignment.query.filter(ResourceAssignment.publish_id.in_(pub_ids)).all()

    @staticmethod
    def find_assignment(publish_id: int, student_id: int) -> ResourceAssignment | None:
        return ResourceAssignment.query.filter_by(publish_id=publish_id, student_id=student_id).first()

    @staticmethod
    def commit() -> None:
        from app.extensions import db

        db.session.commit()

    @staticmethod
    def revoke_publish(record: ResourcePublish) -> None:
        record.revoked = True
        record.revoked_at = datetime.datetime.now()
        from app.extensions import db

        db.session.commit()
