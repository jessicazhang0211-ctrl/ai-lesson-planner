from .shared import *
from .shared import _get_uid, _normalize_header, _find_header_row, _debug_headers_allowed
from app.models.user import User
from app.models.student_profile import StudentProfile

@bp.route('/<int:cid>/export', methods=['GET'])
def export_class(cid: int):
    uid = _get_uid()
    if not uid:
        return err('missing X-User-Id', http_status=401)
    c = Classroom.query.get(cid)
    if not c or c.created_by != uid:
        return err('class not found', http_status=404)

    fmt = (request.args.get('format') or '').lower()
    students = c.students or []
    if fmt == 'csv':
        si = io.StringIO()
        writer = csv.writer(si)
        writer.writerow(['name', 'stu_id', 'status', 'parent_phone', 'accuracy', 'submit', 'created_at'])
        for s in students:
            writer.writerow([s.name or '', s.stu_id or '', s.status or '', s.parent_phone or '', s.accuracy if s.accuracy is not None else '', s.submit if s.submit is not None else '', s.created_at.strftime('%Y-%m-%d %H:%M:%S') if s.created_at else ''])
        output = si.getvalue()
        resp = make_response(output)
        resp.headers['Content-Type'] = 'text/csv; charset=utf-8'
        resp.headers['Content-Disposition'] = f'attachment; filename=class_{c.id}_students.csv'
        return resp
    if fmt in ('xlsx', 'excel'):
        if not openpyxl:
            return err('xlsx export requires openpyxl', http_status=500)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Students'
        headers = ['name', 'stu_id', 'status', 'parent_phone', 'accuracy', 'submit', 'created_at']
        ws.append(headers)
        for s in students:
            ws.append([s.name or '', s.stu_id or '', s.status or '', s.parent_phone or '', s.accuracy if s.accuracy is not None else '', s.submit if s.submit is not None else '', s.created_at.strftime('%Y-%m-%d %H:%M:%S') if s.created_at else ''])
        # auto width
        for i, col in enumerate(ws.columns, 1):
            max_length = 0
            for cell in col:
                try:
                    v = str(cell.value or '')
                except Exception:
                    v = ''
                if len(v) > max_length:
                    max_length = len(v)
            ws.column_dimensions[get_column_letter(i)].width = min(50, max(10, max_length + 2))
        bio = io.BytesIO()
        wb.save(bio)
        bio.seek(0)
        resp = make_response(bio.read())
        resp.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        resp.headers['Content-Disposition'] = f'attachment; filename=class_{c.id}_students.xlsx'
        return resp

    # default: return JSON with students
    return ok(c.to_dict(include_students=True))


@bp.route('/<int:cid>/import', methods=['POST'])
def import_students(cid: int):
    """Accepts JSON body with {'students': [...]} or raw CSV in request data or form field 'csv'.
    Matching is attempted by stu_id (when provided) to update existing students; otherwise new students are created.
    """
    uid = _get_uid()
    if not uid:
        return err('missing X-User-Id', http_status=401)
    c = Classroom.query.get(cid)
    if not c or c.created_by != uid:
        return err('class not found', http_status=404)

    added = 0
    updated = 0
    account_created = 0
    invalid_header_msg = 'invalid header: expected name (or 姓名)'

    year_part = datetime.datetime.now().year
    class_part = f"{cid % 100:02d}"
    stu_prefix = f"{year_part}0{class_part}"
    seq_max = 0
    existing_students = Student.query.filter_by(class_id=cid).all()
    for es in existing_students:
        sid = (es.stu_id or '').strip()
        if not sid.startswith(stu_prefix):
            continue
        tail = sid[len(stu_prefix):]
        if len(tail) != 3 or not tail.isdigit():
            continue
        seq_max = max(seq_max, int(tail))
    next_seq = seq_max + 1

    def _next_auto_stu_id():
        nonlocal next_seq
        if next_seq > 999:
            raise ValueError('student id sequence exceeded 999 for this class/year')
        sid = f"{stu_prefix}{next_seq:03d}"
        next_seq += 1
        return sid

    data = request.get_json(silent=True)
    # case 1: JSON payload with students array
    if data and isinstance(data, dict) and 'students' in data and isinstance(data['students'], list):
        rows = data['students']
    else:
        # case 2: file upload via multipart/form-data
        if 'file' in request.files:
            f = request.files['file']
            filename = (f.filename or '').lower()
            content = f.read()
            # xlsx
            if filename.endswith('.xlsx') or (openpyxl and content[:2] == b'PK'):
                if not openpyxl:
                    return err('xlsx import requires openpyxl', http_status=500)
                wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
                ws = wb.active
                rows_iter = list(ws.iter_rows(values_only=True))
                if not rows_iter:
                    return err('empty xlsx', http_status=400)
                header, header_idx = _find_header_row(rows_iter)
                if header is None:
                    data = {'parsed_header': rows_iter[0]} if _debug_headers_allowed() else None
                    return err(invalid_header_msg, http_status=400, data=data)
                # trim leading non-header rows
                if header_idx and header_idx > 0:
                    rows_iter = rows_iter[header_idx:]
                # map indexes
                def find_idx(keys):
                    for k in keys:
                        if k in header:
                            return header.index(k)
                    return None
                idx_name = find_idx(['name','姓名'])
                idx_sid = find_idx(['stu_id','学号'])
                idx_phone = find_idx(['parent_phone','家长电话'])
                idx_status = find_idx(['status','状态'])
                rows = []
                for row in rows_iter[1:]:
                    name = str(row[idx_name]).strip() if (idx_name is not None and idx_name < len(row) and row[idx_name] is not None) else ''
                    sid = str(row[idx_sid]).strip() if (idx_sid is not None and idx_sid < len(row) and row[idx_sid] is not None) else ''
                    phone = str(row[idx_phone]).strip() if (idx_phone is not None and idx_phone < len(row) and row[idx_phone] is not None) else ''
                    status = str(row[idx_status]).strip() if (idx_status is not None and idx_status < len(row) and row[idx_status] is not None) else 'joined'
                    if not name:
                        continue
                    rows.append({'name': name, 'stu_id': sid, 'parent_phone': phone, 'status': status})
            elif filename.endswith('.xls') or (xlrd and not filename.endswith('.xlsx')):
                # old Excel .xls；若是文本伪装成 .xls 也尝试降级为 CSV/TSV 解析
                if not xlrd:
                    return err('.xls import requires xlrd', http_status=500)
                rows_iter = None
                try:
                    book = xlrd.open_workbook(file_contents=content)
                    sheet = book.sheet_by_index(0)
                    rows_iter = [sheet.row_values(i) for i in range(sheet.nrows)]
                except Exception:
                    rows_iter = None

                if rows_iter:
                    header, header_idx = _find_header_row(rows_iter)
                    if header is None:
                        data = {'parsed_header': rows_iter[0]} if _debug_headers_allowed() else None
                        return err(invalid_header_msg, http_status=400, data=data)
                    if header_idx and header_idx > 0:
                        rows_iter = rows_iter[header_idx:]
                    def find_idx(keys):
                        for k in keys:
                            if k in header:
                                return header.index(k)
                        return None
                    idx_name = find_idx(['name','姓名'])
                    idx_sid = find_idx(['stu_id','学号'])
                    idx_phone = find_idx(['parent_phone','家长电话'])
                    idx_status = find_idx(['status','状态'])
                    rows = []
                    for row in rows_iter[1:]:
                        name = str(row[idx_name]).strip() if (idx_name is not None and idx_name < len(row) and row[idx_name] is not None) else ''
                        sid = str(row[idx_sid]).strip() if (idx_sid is not None and idx_sid < len(row) and row[idx_sid] is not None) else ''
                        phone = str(row[idx_phone]).strip() if (idx_phone is not None and idx_phone < len(row) and row[idx_phone] is not None) else ''
                        status = str(row[idx_status]).strip() if (idx_status is not None and idx_status < len(row) and row[idx_status] is not None) else 'joined'
                        if not name:
                            continue
                        rows.append({'name': name, 'stu_id': sid, 'parent_phone': phone, 'status': status})
                else:
                    # fallback: treat as text (csv/tsv) misnamed as .xls
                    try:
                        txt = content.decode('utf-8', errors='ignore')
                        if not txt.strip():
                            return err('invalid xls file', http_status=400)
                        first_line = txt.splitlines()[0] if txt.splitlines() else ''
                        delimiter = '\t' if '\t' in first_line else ','
                        reader = csv.reader(io.StringIO(txt), delimiter=delimiter)
                        lines = [r for r in reader if any(cell.strip() for cell in r)]
                        if not lines:
                            return err('invalid xls file', http_status=400)
                        header, header_idx = _find_header_row(lines)
                        if header is None:
                            data = {'parsed_header': lines[0]} if _debug_headers_allowed() else None
                            return err(invalid_header_msg, http_status=400, data=data)
                        if header_idx and header_idx > 0:
                            lines = lines[header_idx:]
                        try:
                            idx_name = header.index('name') if 'name' in header else (header.index('姓名') if '姓名' in header else None)
                        except ValueError:
                            idx_name = None
                        try:
                            idx_sid = header.index('stu_id') if 'stu_id' in header else (header.index('学号') if '学号' in header else None)
                        except ValueError:
                            idx_sid = None
                        try:
                            idx_phone = header.index('parent_phone') if 'parent_phone' in header else (header.index('家长电话') if '家长电话' in header else None)
                        except ValueError:
                            idx_phone = None
                        try:
                            idx_status = header.index('status') if 'status' in header else (header.index('状态') if '状态' in header else None)
                        except ValueError:
                            idx_status = None
                        rows = []
                        for r in lines[1:]:
                            name = r[idx_name].strip() if (idx_name is not None and idx_name < len(r)) else ''
                            sid = r[idx_sid].strip() if (idx_sid is not None and idx_sid < len(r)) else ''
                            phone = r[idx_phone].strip() if (idx_phone is not None and idx_phone < len(r)) else ''
                            status = r[idx_status].strip() if (idx_status is not None and idx_status < len(r)) else 'joined'
                            if not name:
                                continue
                            rows.append({'name': name, 'stu_id': sid, 'parent_phone': phone, 'status': status})
                    except Exception:
                        return err('invalid xls file', http_status=400)
            else:
                # assume CSV
                txt = content.decode('utf-8', errors='ignore')
                reader = csv.reader(io.StringIO(txt))
                lines = [r for r in reader if any(cell.strip() for cell in r)]
                if not lines:
                    return err('empty csv', http_status=400)
                header, header_idx = _find_header_row(lines)
                if header is None:
                    data = {'parsed_header': lines[0]} if _debug_headers_allowed() else None
                    return err(invalid_header_msg, http_status=400, data=data)
                if header_idx and header_idx > 0:
                    lines = lines[header_idx:]
                try:
                    idx_name = header.index('name') if 'name' in header else (header.index('姓名') if '姓名' in header else None)
                except ValueError:
                    idx_name = None
                try:
                    idx_sid = header.index('stu_id') if 'stu_id' in header else (header.index('学号') if '学号' in header else None)
                except ValueError:
                    idx_sid = None
                try:
                    idx_phone = header.index('parent_phone') if 'parent_phone' in header else (header.index('家长电话') if '家长电话' in header else None)
                except ValueError:
                    idx_phone = None
                try:
                    idx_status = header.index('status') if 'status' in header else (header.index('状态') if '状态' in header else None)
                except ValueError:
                    idx_status = None
                rows = []
                for r in lines[1:]:
                    name = r[idx_name].strip() if (idx_name is not None and idx_name < len(r)) else ''
                    sid = r[idx_sid].strip() if (idx_sid is not None and idx_sid < len(r)) else ''
                    phone = r[idx_phone].strip() if (idx_phone is not None and idx_phone < len(r)) else ''
                    status = r[idx_status].strip() if (idx_status is not None and idx_status < len(r)) else 'joined'
                    if not name:
                        continue
                    rows.append({'name': name, 'stu_id': sid, 'parent_phone': phone, 'status': status})
        else:
            # try to read CSV from raw body or form fallback
            raw = ''
            if request.form.get('csv'):
                raw = request.form.get('csv')
            else:
                raw = (request.data or b'').decode('utf-8', errors='ignore')
            if not raw:
                return err('no students data provided', http_status=400)
            reader = csv.reader(io.StringIO(raw))
            lines = [r for r in reader if any(cell.strip() for cell in r)]
            if not lines:
                return err('empty csv', http_status=400)
            header = [_normalize_header(h) for h in lines[0]]
            hk = set(header)
            if not ('name' in hk or '姓名' in hk):
                data = {'parsed_header': header} if _debug_headers_allowed() else None
                return err(invalid_header_msg, http_status=400, data=data)
            # find indexes
            try:
                idx_name = header.index('name') if 'name' in header else (header.index('姓名') if '姓名' in header else None)
            except ValueError:
                idx_name = None
            try:
                idx_sid = header.index('stu_id') if 'stu_id' in header else (header.index('学号') if '学号' in header else None)
            except ValueError:
                idx_sid = None
            try:
                idx_phone = header.index('parent_phone') if 'parent_phone' in header else (header.index('家长电话') if '家长电话' in header else None)
            except ValueError:
                idx_phone = None
            try:
                idx_status = header.index('status') if 'status' in header else (header.index('状态') if '状态' in header else None)
            except ValueError:
                idx_status = None

            rows = []
            for r in lines[1:]:
                name = r[idx_name].strip() if (idx_name is not None and idx_name < len(r)) else ''
                sid = r[idx_sid].strip() if (idx_sid is not None and idx_sid < len(r)) else ''
                phone = r[idx_phone].strip() if (idx_phone is not None and idx_phone < len(r)) else ''
                status = r[idx_status].strip() if (idx_status is not None and idx_status < len(r)) else 'joined'
                if not name:
                    continue
                rows.append({'name': name, 'stu_id': sid, 'parent_phone': phone, 'status': status})

    # process rows
    touched_students = []
    for item in rows:
        name = (item.get('name') or '').strip()
        if not name:
            continue
        input_stu_id = (item.get('stu_id') or '').strip()
        status = (item.get('status') or 'joined')
        parent_phone = item.get('parent_phone') or ''
        accuracy = item.get('accuracy') if 'accuracy' in item else None
        submit = item.get('submit') if 'submit' in item else None

        existing = None
        if input_stu_id:
            existing = Student.query.filter_by(class_id=cid, stu_id=input_stu_id).first()
        if existing:
            existing.name = name
            existing.status = status
            existing.parent_phone = parent_phone
            if accuracy is not None:
                try:
                    existing.accuracy = int(accuracy)
                except Exception:
                    pass
            if submit is not None:
                try:
                    existing.submit = int(submit)
                except Exception:
                    pass
            updated += 1
            touched_students.append(existing)
        else:
            s = Student(
                name=name,
                stu_id=_next_auto_stu_id(),
                status=status,
                parent_phone=parent_phone,
                accuracy=(int(accuracy) if (accuracy is not None and str(accuracy).strip() != '') else None),
                submit=(int(submit) if (submit is not None and str(submit).strip() != '') else None),
                class_id=cid
            )
            db.session.add(s)
            added += 1
            touched_students.append(s)

    db.session.flush()

    for s in touched_students:
        profile = StudentProfile.query.filter_by(student_id=s.id).first()
        if profile:
            user = User.query.get(profile.user_id)
            if user and user.name != s.name:
                user.name = s.name
            continue

        raw = (s.stu_id or f"s{s.id}").strip()
        local = ''.join(ch for ch in raw if ch.isalnum()) or f"s{s.id}"
        email = f"student-{cid}-{local}@auto.local"
        suffix = 1
        while User.query.filter_by(email=email).first():
            email = f"student-{cid}-{local}-{suffix}@auto.local"
            suffix += 1

        user = User(name=s.name or f"student_{s.id}", email=email)
        user.set_password("123456")
        db.session.add(user)
        db.session.flush()

        sp = StudentProfile(user_id=user.id, class_id=cid, student_id=s.id)
        db.session.add(sp)
        account_created += 1

    db.session.commit()
    # return summary and updated class data
    return ok({'added': added, 'updated': updated, 'account_created': account_created, 'class': c.to_dict(include_students=True)}, 'import complete')


