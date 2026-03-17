from .shared import *
from .shared import _get_uid

@bp.route('/<int:cid>/stats', methods=['GET'])
def class_stats(cid: int):
    uid = _get_uid()
    if not uid:
        return err('missing X-User-Id', http_status=401)
    c = Classroom.query.get(cid)
    if not c or c.created_by != uid:
        return err('class not found', http_status=404)

    students = c.students or []
    total = len(students)
    submitted = sum(1 for s in students if (s.submit is not None and s.submit > 0))
    acc_values = [s.accuracy for s in students if s.accuracy is not None]
    avg_acc = (sum(acc_values) / len(acc_values)) if acc_values else None
    pending = sum(1 for s in students if s.status == 'pending')

    return ok({'total': total, 'submitted': submitted, 'avg_accuracy': (round(avg_acc,2) if avg_acc is not None else None), 'pending': pending})

