# app\utils\response.py
from flask import jsonify

def ok(data=None, message="ok"):
    return jsonify({"code": 0, "message": message, "data": data or {}})

def err(message="error", code=1, http_status=400, data=None):
    return jsonify({"code": code, "message": message, "data": data or {}}), http_status
