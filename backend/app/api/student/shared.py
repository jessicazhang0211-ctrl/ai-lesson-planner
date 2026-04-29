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


def _resolve_exercise_structured(exercise):
    if not exercise:
        return None

    candidates = [
        getattr(exercise, "content_json", None),
        _strip_meta_prefix(getattr(exercise, "description", None)),
    ]
    for raw in candidates:
        if not raw:
            continue
        try:
            parsed = extract_json(raw)
            normalized = _normalize_structured_exercise(parsed)
            if normalized:
                return normalized
        except Exception:
            continue

    description = _strip_meta_prefix(getattr(exercise, "description", None))
    if description:
        return _parse_formatted_exercise(description)
    return None


def _strip_meta_prefix(text):
    raw = str(text or "")
    if not raw.startswith("__META__"):
        return raw.strip()
    try:
        _, body = raw.split("__\n", 1)
        return body.strip()
    except Exception:
        return raw.strip()


def _parse_score_text(text):
    m = re.search(r"(\d+)\s*[分|]?$", str(text or "").strip())
    return int(m.group(1)) if m else 0


def _parse_answer_text(text):
    raw = str(text or "").strip()
    if not raw:
        return ""
    parts = [p.strip() for p in re.split(r"[、,，/]+", raw) if p.strip()]
    return parts if len(parts) > 1 else raw


def _infer_question_type(block_text, answer_text):
    text = str(block_text or "").lower()
    answer = str(answer_text or "").strip().lower()
    if "判断" in text or answer in ("true", "false", "对", "错"):
        return "true_false"

    option_labels = re.findall(r"(?:^|\n)\s*([A-D])[.．、:：)]\s*", str(block_text or ""), flags=re.IGNORECASE)
    if option_labels:
        answer_tokens = [x.strip().upper() for x in re.split(r"[、,，/]+", answer) if x.strip()]
        if len(answer_tokens) > 1:
            return "multi"
        return "single"

    if "填空" in text or "____" in text or "___" in text:
        return "fill"

    if any(k in text for k in ("简答", "解答", "说明", "作文", "论述")):
        return "short"
    return "short"


def _parse_formatted_exercise(text):
    raw = str(text or "").strip()
    if not raw:
        return None

    block_matches = list(re.finditer(r"(?m)^\s*(\d+)[.．、]\s*", raw))
    if not block_matches:
        return None

    questions = []
    for idx, match in enumerate(block_matches):
        start = match.start()
        end = block_matches[idx + 1].start() if idx + 1 < len(block_matches) else len(raw)
        block = raw[start:end].strip()
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue

        first = re.sub(r"^\s*\d+[.．、]\s*", "", lines[0]).strip()
        stem_parts = []
        options = []
        answer_text = ""
        analysis_text = ""
        score = 0
        mode = "stem"

        for line in [first] + lines[1:]:
            if re.match(r"^[A-Da-d][.．、:：)]\s*", line):
                mode = "options"
                options.append(re.sub(r"^[A-Da-d][.．、:：)]\s*", "", line).strip())
                continue
            if line.startswith("答案") or line.lower().startswith("answer"):
                answer_text = re.split(r"[:：]", line, maxsplit=1)[-1].strip()
                mode = "meta"
                continue
            if line.startswith("解析") or line.lower().startswith("analysis"):
                analysis_text = re.split(r"[:：]", line, maxsplit=1)[-1].strip()
                mode = "meta"
                continue
            if line.startswith("分值") or line.lower().startswith("score"):
                score = _parse_score_text(re.split(r"[:：]", line, maxsplit=1)[-1].strip())
                mode = "meta"
                continue

            if mode == "options" and options and not answer_text:
                options[-1] = f"{options[-1]} {line}".strip()
            elif mode == "meta" and analysis_text and not answer_text:
                analysis_text = f"{analysis_text} {line}".strip()
            else:
                stem_parts.append(line)

        stem = " ".join([x for x in stem_parts if x]).strip()
        qtype = _infer_question_type(block, answer_text)
        answer = _parse_answer_text(answer_text)
        if qtype == "true_false":
            ans = str(answer).strip().lower()
            if ans in ("对", "正确", "t", "yes", "1"):
                answer = "true"
            elif ans in ("错", "错误", "f", "no", "0"):
                answer = "false"
            else:
                answer = ans

        question = {
            "id": f"q{len(questions) + 1}",
            "type": qtype,
            "stem": stem or first,
            "score": score,
            "answer": answer,
        }
        if options:
            question["options"] = options
        if analysis_text:
            question["analysis"] = analysis_text
        questions.append(question)

    return {"questions": questions} if questions else None


def _normalize_structured_exercise(value):
    if not isinstance(value, dict):
        return None
    questions = value.get("questions")
    if not isinstance(questions, list) or not questions:
        return None

    normalized = []
    for idx, item in enumerate(questions):
        if not isinstance(item, dict):
            continue
        q = dict(item)
        q["id"] = str(q.get("id") or f"q{idx + 1}")
        q["type"] = str(q.get("type") or _infer_question_type(q.get("stem"), q.get("answer"))).lower()
        q["stem"] = str(q.get("stem") or q.get("question") or "").strip()
        try:
            q["score"] = int(q.get("score") or 0)
        except Exception:
            q["score"] = 0
        normalized.append(q)

    return {"questions": normalized} if normalized else None


def _normalize_answer(v):
    if v is None:
        return ""
    if isinstance(v, list):
        return [str(x).strip().lower() for x in v]
    return str(v).strip().lower()


def _split_answer_tokens(v, expected_len: int | None = None):
    if isinstance(v, list):
        return [str(x).strip().lower() for x in v if str(x).strip()]

    text = str(v or "").strip().lower().replace("\u3000", " ")
    if not text:
        return []

    # Primary separators for multi-blank answers.
    parts = [x.strip() for x in re.split(r"[，,、;；|]+", text) if x.strip()]

    # Fallback: support space-separated inputs like "30 3" when multiple blanks are expected.
    if len(parts) <= 1 and expected_len and expected_len > 1:
        parts = [x.strip() for x in re.split(r"\s+", text) if x.strip()]

    return parts


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
            ua_tokens = _split_answer_tokens(user_answer, expected_len=len(an))
            an_tokens = _split_answer_tokens(an, expected_len=len(an))
            return ua_tokens == an_tokens
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



