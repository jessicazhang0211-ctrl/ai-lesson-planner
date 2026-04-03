import time
import re
from functools import wraps
from flask import request, g
import jwt
from app.config import Config
from app.utils.response import err


def generate_token(user_id: int, exp_seconds: int = None):
    if exp_seconds is None:
        exp_seconds = Config.JWT_EXP_SECONDS
    payload = {
        "user_id": int(user_id),
        "exp": int(time.time()) + int(exp_seconds)
    }
    token = jwt.encode(payload, Config.JWT_SECRET, algorithm=Config.JWT_ALGORITHM)
    # PyJWT returns str in modern versions
    if isinstance(token, bytes):
        token = token.decode()
    return token


def decode_token(token: str):
    try:
        payload = jwt.decode(token, Config.JWT_SECRET, algorithms=[Config.JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise
    except Exception:
        raise


def validate_password_strength(password: str):
    """Return (ok, message)."""
    p = password or ""
    if len(p) < 8:
        return False, "password must be at least 8 characters"
    if not re.search(r"[A-Z]", p):
        return False, "password must include an uppercase letter"
    if not re.search(r"[a-z]", p):
        return False, "password must include a lowercase letter"
    if not re.search(r"\d", p):
        return False, "password must include a digit"
    if not re.search(r"[^A-Za-z0-9]", p):
        return False, "password must include a special character"
    return True, "ok"


def token_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        # Allow CORS preflight without token so browsers can proceed to real request
        if request.method == "OPTIONS":
            return f(*args, **kwargs)

        auth = request.headers.get("Authorization", "")
        token = None
        if auth and auth.lower().startswith("bearer "):
            token = auth.split(None, 1)[1]
        else:
            # fallback to X-Access-Token header
            token = request.headers.get("X-Access-Token") or request.args.get("token")

        if not token:
            return err("missing token", http_status=401)

        try:
            payload = decode_token(token)
            g.current_user_id = int(payload.get("user_id", 0))
        except Exception as e:
            return err("invalid or expired token", http_status=401)

        # 学生账号若仍使用默认初始密码，强制先改密
        try:
            from app.models.user import User
            from app.models.student_profile import StudentProfile

            uid = int(getattr(g, "current_user_id", 0) or 0)
            if uid:
                profile = StudentProfile.query.filter_by(user_id=uid).first()
                if profile:
                    u = User.query.get(uid)
                    if u and u.check_password("123456"):
                        g.must_change_password = True
                        # Allow student-side read/write APIs in development even with initial password,
                        # otherwise frontend may look like a CORS failure while actually being blocked by auth.
                        if request.path != "/api/user/change-password" and not request.path.startswith("/api/student/"):
                            return err(
                                "password reset required",
                                http_status=403,
                                data={"must_change_password": True}
                            )
        except Exception:
            # 不因附加校验影响已有鉴权流程
            pass

        return f(*args, **kwargs)

    return wrapped
