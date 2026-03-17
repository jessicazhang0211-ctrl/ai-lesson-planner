from flask import Blueprint, request, Response, make_response, g
from flask import current_app
from app.utils.response import ok, err
from app.utils.auth import token_required
from app.utils.auth import decode_token
from app.extensions import db
from app.models.classroom import Classroom, Student
from app.models.resource_publish import ResourcePublish
from app.models.resource_assignment import ResourceAssignment
import datetime, random, string
import io, csv
try:
    import openpyxl
    from openpyxl.utils import get_column_letter
except Exception:
    openpyxl = None
try:
    import xlrd
except Exception:
    xlrd = None

from .blueprint import bp


def _gen_code(n=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=n))


def _normalize_header(h):
    """Normalize a header cell: strip whitespace, remove BOM, lower-case."""
    if h is None:
        return ''
    try:
        s = str(h)
    except Exception:
        s = ''
    return s.lstrip('\ufeff').strip().lower()


def _find_header_row(rows):
    """Find the first row that contains required header columns (name or 姓名)."""
    max_scan = min(len(rows), 8)
    for i in range(max_scan):
        norm = [_normalize_header(h) for h in rows[i]]
        hk = set(norm)
        if ('name' in hk or '姓名' in hk):
            return norm, i
    return None, None


def _debug_headers_allowed():
    # allow when app is in debug or when request explicitly asks for header debug
    try:
        if getattr(current_app, 'debug', False):
            return True
    except Exception:
        pass
    v = (request.args.get('debug_headers') or '').lower()
    return v in ('1', 'true', 'yes')


def _get_uid():
    uid = (request.headers.get("X-User-Id") or "").strip()
    try:
        if uid:
            return int(uid)
    except ValueError:
        pass

    auth = request.headers.get("Authorization", "")
    token = None
    if auth and auth.lower().startswith("bearer "):
        token = auth.split(None, 1)[1]
    else:
        token = request.headers.get("X-Access-Token") or request.args.get("token")

    if not token:
        return None
    try:
        payload = decode_token(token)
        return int(payload.get("user_id", 0) or 0) or None
    except Exception:
        return None



