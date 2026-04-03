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
import re

try:
    import google.generativeai as genai
except Exception:
    genai = None

from .blueprint import bp

if genai and Config.GEMINI_API_KEY:
    genai.configure(api_key=Config.GEMINI_API_KEY)


def _load_ids(raw):
    try:
        values = json.loads(raw) if raw else []
        if not isinstance(values, list):
            return []
        normalized = []
        for v in values:
            try:
                normalized.append(int(v))
            except Exception:
                continue
        return normalized
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


def _normalize_lang(lang: str):
    v = str(lang or "zh").lower()
    return "en" if v.startswith("en") else "zh"


def _translate_analysis_rule_based(analysis: dict):
    if not isinstance(analysis, dict):
        return None

    zh_to_en = {
        "暂无明显薄弱点": "No obvious weak point yet",
        "数据不足": "Insufficient data",
        "表现优秀": "Excellent performance",
        "稳定提升": "Steady improvement",
        "需要加强": "Needs reinforcement",
        "完成更多作业后再进行分析": "Complete more assignments for a more reliable analysis",
        "保持节奏，尝试提高综合题": "Keep the pace and challenge more comprehensive questions",
        "建议巩固错题题型": "Focus on consolidating question types you often get wrong",
        "优先补齐基础题型": "Prioritize strengthening foundational question types"
    }

    def _tx(value):
        raw = str(value or "").strip()
        if not raw:
            return raw
        if raw in zh_to_en:
            return zh_to_en[raw]

        m = re.match(r"^(单选|多选|判断|填空|简答|其他)题错误率偏高$", raw)
        if m:
            tmap = {
                "单选": "single-choice",
                "多选": "multiple-choice",
                "判断": "true/false",
                "填空": "fill-in-the-blank",
                "简答": "short-answer",
                "其他": "other"
            }
            qtype = tmap.get(m.group(1), "specific")
            return f"High error rate in {qtype} questions"
        return raw

    return {
        "weak_spot": _tx(analysis.get("weak_spot", "")),
        "study_state": _tx(analysis.get("study_state", "")),
        "study_tip": _tx(analysis.get("study_tip", ""))
    }


def _localize_analysis(analysis: dict, lang: str):
    lang = _normalize_lang(lang)
    if lang == "zh":
        return analysis
    if not isinstance(analysis, dict):
        return analysis

    if not genai or not Config.GEMINI_API_KEY:
        return _translate_analysis_rule_based(analysis) or analysis

    try:
        prompt = (
            "Translate the following JSON values into concise educational English. "
            "Keep keys unchanged and return JSON only.\n"
            "Keys: weak_spot, study_state, study_tip.\n"
            f"Input JSON: {json.dumps(analysis, ensure_ascii=False)}"
        )
        localized = _extract_json(ai_service.generate_text(prompt))
        if isinstance(localized, dict) and all(k in localized for k in ("weak_spot", "study_state", "study_tip")):
            return localized
    except Exception:
        pass

    return _translate_analysis_rule_based(analysis) or analysis



