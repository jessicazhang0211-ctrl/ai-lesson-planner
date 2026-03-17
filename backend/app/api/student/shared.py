from flask import Blueprint, g, request
from app.utils.auth import token_required
from app.utils.response import ok, err
from app.extensions import db
from app.models.student_profile import StudentProfile
from app.models.resource_publish import ResourcePublish
from app.models.resource_assignment import ResourceAssignment
from app.models.exercise_submission import ExerciseSubmission
from app.models.lesson import Lesson
from app.models.exercise import Exercise
from app.models.classroom import Classroom
from app.config import Config
from app.services.ai_service import ai_service
from app.utils.json_handlers import extract_json
import json
import datetime

try:
    import google.generativeai as genai
except Exception:
    genai = None

from .blueprint import bp

if genai and Config.GEMINI_API_KEY:
    genai.configure(api_key=Config.GEMINI_API_KEY)


def _load_ids(raw):
    try:
        return json.loads(raw) if raw else []
    except Exception:
        return []


def _normalize_answer(v):
    if v is None:
        return ""
    if isinstance(v, list):
        return [str(x).strip().lower() for x in v]
    return str(v).strip().lower()


def _grade_objective(q, user_answer):
    qtype = (q.get("type") or "").lower()
    answer = q.get("answer")
    if qtype in ("single", "true_false"):
        return _normalize_answer(user_answer) == _normalize_answer(answer)
    if qtype == "multi":
        ua = _normalize_answer(user_answer)
        an = _normalize_answer(answer)
        if not isinstance(ua, list):
            ua = [x for x in str(user_answer).replace(" ", "").split(",") if x]
            ua = [x.lower() for x in ua]
        if not isinstance(an, list):
            an = [x for x in str(answer).replace(" ", "").split(",") if x]
            an = [x.lower() for x in an]
        return sorted(ua) == sorted(an)
    if qtype == "fill":
        ua = _normalize_answer(user_answer)
        an = _normalize_answer(answer)
        if isinstance(an, list):
            if not isinstance(ua, list):
                ua = [x.strip().lower() for x in str(user_answer).split(",")]
            return ua == an
        return ua == an
    return None


def _extract_json(text: str):
    return extract_json(text)


def _type_label(t: str):
    t = (t or "").lower()
    return {
        "single": "单选",
        "multi": "多选",
        "true_false": "判断",
        "fill": "填空",
        "short": "简答",
        "essay": "简答"
    }.get(t, "其他")


def _rule_based_analysis(avg_score_all, wrong_rate_map):
    if wrong_rate_map:
        worst = max(wrong_rate_map.items(), key=lambda x: x[1])[0]
        weak_spot = f"{_type_label(worst)}题错误率偏高"
    else:
        weak_spot = "暂无明显薄弱点"

    if avg_score_all is None:
        study_state = "数据不足"
        study_tip = "完成更多作业后再进行分析"
    elif avg_score_all >= 85:
        study_state = "表现优秀"
        study_tip = "保持节奏，尝试提高综合题"
    elif avg_score_all >= 70:
        study_state = "稳定提升"
        study_tip = "建议巩固错题题型"
    else:
        study_state = "需要加强"
        study_tip = "优先补齐基础题型"

    return {
        "weak_spot": weak_spot,
        "study_state": study_state,
        "study_tip": study_tip
    }


def _ai_analysis(summary_text: str):
    if not genai or not Config.GEMINI_API_KEY:
        return None
    if not summary_text:
        return None
    try:
        prompt = (
            "你是教育数据分析助手。请根据以下学生作业表现摘要，输出 JSON，格式为："
            "{\"weak_spot\":\"...\",\"study_state\":\"...\",\"study_tip\":\"...\"}\n"
            "仅输出 JSON，不要额外解释。\n\n"
            f"摘要：{summary_text}"
        )
        data = _extract_json(ai_service.generate_text(prompt))
        if isinstance(data, dict) and all(k in data for k in ("weak_spot", "study_state", "study_tip")):
            return data
    except Exception:
        return None
    return None



