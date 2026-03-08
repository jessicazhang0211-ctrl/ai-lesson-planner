import time
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

        return f(*args, **kwargs)

    return wrapped
