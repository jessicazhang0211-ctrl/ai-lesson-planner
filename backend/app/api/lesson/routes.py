# app/api/lesson/routes.py
from flask import Blueprint, request, g
from app.utils.response import ok, err
from app.config import Config

from app.extensions import db
from app.models.lesson import Lesson
from app.models.lesson_edit_log import LessonEditLog
from app.models.lesson_workflow import LessonWorkflow
from app.models.generation_log import GenerationLog
from app.models.resource_publish import ResourcePublish
from app.models.resource_assignment import ResourceAssignment
from app.models.exercise_submission import ExerciseSubmission
from app.models.exercise import Exercise
from app.models.assignment_analysis import AssignmentAnalysis
from app.models.validation_log import ValidationLog
from app.schemas.lesson_schema import validate_lesson_payload
from app.utils.auth import token_required
from app.services.ai_service import ai_service
from app.services.math_rule_service import (
    build_retrieval_context_block,
    generate_math_tooling_bundle,
    retrieve_math_knowledge,
    verify_math_content,
)
from app.services.math_render_service import build_formula_hints, build_diagram_suggestions
from app.services.knowledge_base_service import build_knowledge_injection_context
from app.utils.json_handlers import extract_json_three_stage, safe_json_loads
import datetime, json
import os
import re
import difflib

bp = Blueprint("lesson", __name__, url_prefix="/api/lesson")
_EXAMPLE_STRUCTURE_TEMPLATE = None
_UK_GUARDRAILS = None
_UK_LESSON_SCHEMA = None

_AMERICANISM_HINTS = [
    "math class",
    "first grade",
    "second grade",
    "third grade",
    "fourth grade",
    "fifth grade",
    "sixth grade",
    "eraser",
    "cell phone",
    "zip code",
]

_SAFEGUARDING_TERMS = [
    "self-harm",
    "suicide",
    "abuse",
    "neglect",
    "sexual",
    "extremist",
    "radical",
]


def _load_example_structure_template() -> dict:
    global _EXAMPLE_STRUCTURE_TEMPLATE
    if isinstance(_EXAMPLE_STRUCTURE_TEMPLATE, dict):
        return _EXAMPLE_STRUCTURE_TEMPLATE

    template_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "AItest", "example.json")
    )
    with open(template_path, "r", encoding="utf-8") as f:
        _EXAMPLE_STRUCTURE_TEMPLATE = json.load(f)
    return _EXAMPLE_STRUCTURE_TEMPLATE


def _load_uk_guardrails() -> dict:
    global _UK_GUARDRAILS
    if isinstance(_UK_GUARDRAILS, dict):
        return _UK_GUARDRAILS

    path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "..",
            "AItest",
            "uk_primary_math_model_guardrails.json",
        )
    )
    with open(path, "r", encoding="utf-8") as f:
        _UK_GUARDRAILS = json.load(f)
    return _UK_GUARDRAILS


def _load_uk_lesson_schema() -> dict:
    global _UK_LESSON_SCHEMA
    if isinstance(_UK_LESSON_SCHEMA, dict):
        return _UK_LESSON_SCHEMA

    path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "..",
            "AItest",
            "uk_primary_math_lesson_plan_schema.json",
        )
    )
    with open(path, "r", encoding="utf-8") as f:
        _UK_LESSON_SCHEMA = json.load(f)
    return _UK_LESSON_SCHEMA


def _normalize_year_group(grade: str) -> str:
    raw = (grade or "").strip()
    if not raw:
        return ""

    zh_map = {
        "小学一年级": "Year 1",
        "小学二年级": "Year 2",
        "小学三年级": "Year 3",
        "小学四年级": "Year 4",
        "小学五年级": "Year 5",
        "小学六年级": "Year 6",
    }
    if raw in zh_map:
        return zh_map[raw]

    m = re.search(r"year\s*([1-6])", raw, flags=re.IGNORECASE)
    if m:
        return f"Year {m.group(1)}"

    m_cn = re.search(r"([一二三四五六123456])年级", raw)
    if m_cn:
        cn_digit = m_cn.group(1)
        cn_map = {
            "一": "1",
            "二": "2",
            "三": "3",
            "四": "4",
            "五": "5",
            "六": "6",
        }
        d = cn_map.get(cn_digit, cn_digit)
        return f"Year {d}"

    return raw


def _infer_key_stage(year_group: str) -> str:
    if year_group in ("Year 1", "Year 2"):
        return "KS1"
    if year_group in ("Year 3", "Year 4"):
        return "Lower KS2"
    if year_group in ("Year 5", "Year 6"):
        return "Upper KS2"
    return "KS1"


def _collect_text_nodes(value, out=None):
    if out is None:
        out = []
    if isinstance(value, str):
        s = value.strip()
        if s:
            out.append(s)
        return out
    if isinstance(value, list):
        for item in value:
            _collect_text_nodes(item, out)
        return out
    if isinstance(value, dict):
        for v in value.values():
            _collect_text_nodes(v, out)
        return out
    return out


def _validate_uk_thesis_payload(obj: dict, year_group: str) -> list:
    errors = []
    if not isinstance(obj, dict):
        return ["$: expected object"]

    schema = _load_uk_lesson_schema()
    required_top = schema.get("required") or []
    for key in required_top:
        if key not in obj:
            errors.append(f"missing_top_field:{key}")

    metadata = obj.get("metadata")
    if not isinstance(metadata, dict):
        errors.append("metadata: expected object")
    else:
        if metadata.get("locale") != "en-GB":
            errors.append("metadata.locale:not_en_gb")
        if metadata.get("jurisdiction") != "England":
            errors.append("metadata.jurisdiction:not_england")
        refs = metadata.get("curriculum_refs")
        if not isinstance(refs, list) or not [x for x in refs if isinstance(x, str) and x.strip()]:
            errors.append("metadata.curriculum_refs:missing")
        if metadata.get("teacher_review_required") is not True:
            errors.append("metadata.teacher_review_required:false")

    safeguarding = obj.get("safeguarding_and_privacy")
    if not isinstance(safeguarding, dict):
        errors.append("safeguarding_and_privacy: expected object")
    else:
        if safeguarding.get("teacher_review_required") is not True:
            errors.append("safeguarding.teacher_review_required:false")
        if safeguarding.get("pii_expected") is not False:
            errors.append("safeguarding.pii_expected:not_false")

    texts = [x.lower() for x in _collect_text_nodes(obj)]
    joined = "\n".join(texts)
    for term in _AMERICANISM_HINTS:
        if term in joined:
            errors.append(f"americanism:{term}")
            break

    for term in _SAFEGUARDING_TERMS:
        if term in joined:
            errors.append(f"safeguarding_keyword:{term}")
            break

    max_words = 36
    if year_group in ("Year 1", "Year 2"):
        max_words = 22
    elif year_group in ("Year 3", "Year 4"):
        max_words = 30

    candidate_lines = []
    talk = obj.get("mathematical_talk")
    if isinstance(talk, dict):
        candidate_lines.extend([x for x in (talk.get("sentence_stems") or []) if isinstance(x, str)])
    lesson_flow = obj.get("lesson_flow")
    if isinstance(lesson_flow, list):
        for step in lesson_flow:
            if isinstance(step, dict):
                candidate_lines.extend([x for x in (step.get("pupil_actions") or []) if isinstance(x, str)])

    for ln in candidate_lines[:80]:
        word_count = len(re.findall(r"[A-Za-z']+", ln))
        if word_count > max_words:
            errors.append(f"child_text_too_long:{word_count}>{max_words}")
            break

    return errors


def _ensure_legacy_lesson_fields(obj: dict, fallback_title: str) -> dict:
    if not isinstance(obj, dict):
        return obj

    metadata = obj.get("metadata") if isinstance(obj.get("metadata"), dict) else {}
    objectives_obj = obj.get("objectives") if isinstance(obj.get("objectives"), dict) else {}
    flow = obj.get("lesson_flow") if isinstance(obj.get("lesson_flow"), list) else []

    if not isinstance(obj.get("title"), str) or not obj.get("title", "").strip():
        obj["title"] = (
            metadata.get("lesson_title")
            if isinstance(metadata.get("lesson_title"), str) and metadata.get("lesson_title").strip()
            else fallback_title
        )

    success_criteria = objectives_obj.get("success_criteria") if isinstance(objectives_obj.get("success_criteria"), list) else []
    if not isinstance(obj.get("objectives"), list):
        merged = []
        lo = objectives_obj.get("learning_objective")
        if isinstance(lo, str) and lo.strip():
            merged.append(lo.strip())
        merged.extend([x.strip() for x in success_criteria if isinstance(x, str) and x.strip()])
        obj["objectives"] = merged

    if not isinstance(obj.get("steps"), list):
        steps = []
        for step in flow:
            if not isinstance(step, dict):
                continue
            phase = str(step.get("phase") or "step").strip()
            teacher_actions = step.get("teacher_actions") if isinstance(step.get("teacher_actions"), list) else []
            pupil_actions = step.get("pupil_actions") if isinstance(step.get("pupil_actions"), list) else []
            content_parts = []
            if teacher_actions:
                content_parts.append("Teacher: " + " | ".join([str(x).strip() for x in teacher_actions if str(x).strip()]))
            if pupil_actions:
                content_parts.append("Pupil: " + " | ".join([str(x).strip() for x in pupil_actions if str(x).strip()]))
            if not content_parts:
                continue
            steps.append(
                {
                    "title": phase,
                    "content": "\n".join(content_parts),
                }
            )
        obj["steps"] = steps

    if not isinstance(obj.get("activities"), list):
        steps = obj.get("steps") if isinstance(obj.get("steps"), list) else []
        obj["activities"] = [
            {
                "title": str(step.get("title") or "").strip(),
                "content": str(step.get("content") or "").strip(),
            }
            for step in steps
            if isinstance(step, dict)
        ]

    if not isinstance(obj.get("exercises"), list):
        exercises = []
        tasks = obj.get("practice_tasks") if isinstance(obj.get("practice_tasks"), dict) else {}
        task_items = []
        for k in ["guided_practice", "independent_practice"]:
            v = tasks.get(k)
            if isinstance(v, list):
                task_items.extend(v)
        for item in task_items:
            if isinstance(item, dict):
                q = str(item.get("task") or item.get("prompt") or item.get("question") or "").strip()
                a = str(item.get("expected_answer") or item.get("answer") or item.get("success_indicator") or "").strip()
                if q:
                    fallback_answer = "Expected: correct method and accurate result." if (not a and str(fallback_title).strip()) else "Expected: correct method and accurate result."
                    if not a:
                        fallback_answer = "Expected: correct method and accurate result."
                    exercises.append({"question": q, "answer": a or fallback_answer})
        obj["exercises"] = exercises

    if isinstance(metadata, dict):
        obj.setdefault("lesson_title", metadata.get("lesson_title") or obj.get("title") or fallback_title)
        obj.setdefault("topic", metadata.get("topic") or "")
        obj.setdefault("year_group", metadata.get("year_group") or "")
    if isinstance(obj.get("objectives"), list):
        obj.setdefault("learning_objectives", obj.get("objectives"))
    if isinstance(flow, list):
        obj.setdefault("teaching_sequence", flow)

    return obj


def _skeleton_from_template(template):
    if isinstance(template, dict):
        return {k: _skeleton_from_template(v) for k, v in template.items()}
    if isinstance(template, list):
        if not template:
            return []
        return [_skeleton_from_template(template[0])]
    if isinstance(template, bool):
        return False
    if isinstance(template, int):
        return 0
    if isinstance(template, float):
        return 0.0
    if isinstance(template, str):
        return ""
    return None


def _validate_json_structure_with_template(value, template, path="$", errors=None):
    if errors is None:
        errors = []

    if isinstance(template, dict):
        if not isinstance(value, dict):
            errors.append(f"{path}: expected object")
            return errors

        expected_keys = set(template.keys())
        actual_keys = set(value.keys())
        missing = sorted(expected_keys - actual_keys)
        extra = sorted(actual_keys - expected_keys)

        for k in missing:
            errors.append(f"{path}.{k}: missing key")
        for k in extra:
            errors.append(f"{path}.{k}: unexpected key")

        for k in sorted(expected_keys & actual_keys):
            _validate_json_structure_with_template(value[k], template[k], f"{path}.{k}", errors)
        return errors

    if isinstance(template, list):
        if not isinstance(value, list):
            errors.append(f"{path}: expected array")
            return errors
        if not template:
            return errors
        item_template = template[0]
        for idx, item in enumerate(value):
            _validate_json_structure_with_template(item, item_template, f"{path}[{idx}]", errors)
        return errors

    if template is None:
        if value is not None:
            errors.append(f"{path}: expected null")
        return errors

    if isinstance(template, bool):
        if not isinstance(value, bool):
            errors.append(f"{path}: expected boolean")
        return errors

    if isinstance(template, int):
        if not isinstance(value, int) or isinstance(value, bool):
            errors.append(f"{path}: expected integer")
        return errors

    if isinstance(template, float):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            errors.append(f"{path}: expected number")
        return errors

    if isinstance(template, str):
        if not isinstance(value, str):
            errors.append(f"{path}: expected string")
        return errors

    return errors


def _validate_required_json_fields(obj: dict, required_fields: list) -> tuple:
    missing = [k for k in (required_fields or []) if k not in obj]
    return (len(missing) == 0, missing)


def _validate_semantic_resource_fields(obj: dict) -> list:
    errors = []
    if not isinstance(obj, dict):
        return ["$: expected object"]

    resources_summary = obj.get("resources_summary")
    if not isinstance(resources_summary, list) or len(resources_summary) == 0:
        errors.append("$.resources_summary: must be a non-empty array")
    else:
        valid_lines = [x for x in resources_summary if isinstance(x, str) and x.strip()]
        if not valid_lines:
            errors.append("$.resources_summary: requires at least one non-empty string item")

    external_resources = obj.get("external_resources")
    if not isinstance(external_resources, list) or len(external_resources) == 0:
        errors.append("$.external_resources: must be a non-empty array")
    else:
        ok_item = False
        for i, item in enumerate(external_resources):
            if not isinstance(item, dict):
                errors.append(f"$.external_resources[{i}]: must be object")
                continue
            title = (item.get("title") or "").strip() if isinstance(item.get("title"), str) else ""
            desc = (item.get("description") or "").strip() if isinstance(item.get("description"), str) else ""
            use = (item.get("suggested_use") or "").strip() if isinstance(item.get("suggested_use"), str) else ""
            if title and desc and use:
                ok_item = True
        if not ok_item:
            errors.append("$.external_resources: requires at least one meaningful item (title/description/suggested_use)")

    return errors


def _default_lesson_json_required_fields(lang: str = "zh") -> list:
    return [
        "title",
        "objectives",
        "steps",
        "exercises",
        "anticipated_misconceptions",
        "assessment_for_learning",
        "resources_summary",
        "external_resources",
    ]


def _split_compact_items(raw: str) -> list:
    text = str(raw or "").strip()
    if not text:
        return []
    parts = re.split(r"[\n；;，,、|]+", text)
    return [x.strip() for x in parts if isinstance(x, str) and x.strip()]


def _ensure_display_completeness(obj: dict, key_points: str, lang: str = "zh") -> dict:
    if not isinstance(obj, dict):
        return obj

    is_en = (lang or "zh").lower() == "en"
    topic = str(obj.get("topic") or obj.get("title") or "").strip()
    kp_items = _split_compact_items(key_points) or _split_compact_items(obj.get("key_points") or obj.get("key_challenges") or "")

    def _clean_str_list(value):
        if not isinstance(value, list):
            return []
        return [str(x).strip() for x in value if isinstance(x, str) and str(x).strip()]

    # Objectives
    objectives = _clean_str_list(obj.get("objectives"))
    if not objectives:
        objectives = _clean_str_list(obj.get("learning_objectives"))
    if not objectives:
        base = topic or ("this topic" if is_en else "本课内容")
        if kp_items:
            if is_en:
                objectives = [
                    f"Understand: {kp_items[0]}.",
                    f"Apply: {kp_items[1] if len(kp_items) > 1 else kp_items[0]} in simple tasks.",
                    "Explain reasoning using key vocabulary.",
                ]
            else:
                objectives = [
                    f"掌握：{kp_items[0]}。",
                    f"会应用：{kp_items[1] if len(kp_items) > 1 else kp_items[0]}。",
                    "能用关键术语表达思考过程。",
                ]
        else:
            objectives = [
                f"Understand the core ideas of {base}." if is_en else f"理解{base}的核心概念。",
                f"Apply {base} in simple contexts." if is_en else f"在简单情境中应用{base}。",
                "Explain reasoning with key vocabulary." if is_en else "能用关键术语解释思路。",
            ]
    if len(objectives) < 3:
        base = topic or ("this topic" if is_en else "本课内容")
        filler = [
            f"Understand the core ideas of {base}." if is_en else f"理解{base}的核心概念。",
            f"Apply {base} in simple contexts." if is_en else f"在简单情境中应用{base}。",
            "Explain reasoning with key vocabulary." if is_en else "能用关键术语解释思路。",
        ]
        for item in filler:
            if len(objectives) >= 3:
                break
            if item not in objectives:
                objectives.append(item)
    obj["objectives"] = objectives
    learning_objectives = obj.get("learning_objectives") if isinstance(obj.get("learning_objectives"), list) else []
    if not learning_objectives:
        obj["learning_objectives"] = objectives

    # Misconceptions (map from thesis schema if needed)
    def _mis_response(issue_text: str) -> str:
        issue = str(issue_text or "").lower()
        if any(x in issue for x in ["0", "zero", "零"]):
            return (
                "Teacher shows 3 counters, removes them one by one, asks “How many now?” and labels the empty frame as zero; pupils repeat with their own counters."
                if is_en
                else "教师先摆3个计数器，再逐个拿走并追问“现在有几个？”，强调空框是0；学生操作复现。"
            )
        if any(x in issue for x in ["shape", "size", "形状", "大小"]):
            return (
                "Teacher shows a large ‘2’ and a small ‘8’, asks which number is greater, then matches each to counters to show value is about quantity, not shape size."
                if is_en
                else "教师出示大号“2”和小号“8”，提问哪个数更大，再用计数器对应数量，强调数值与形状大小无关。"
            )
        if any(x in issue for x in ["order", "sequence", "顺序", "排列"]):
            return (
                "Place numbers on a number line, ask pupils to place the missing number and explain why it comes before/after."
                if is_en
                else "用数轴或数列卡片摆放顺序，让学生补空并说明为什么在前/在后。"
            )
        return (
            "Teacher shows an incorrect example, asks pupils to spot the error, then models the correct method and has pupils redo once with support."
            if is_en
            else "教师出示错误示例，请学生找错，再示范正确做法并让学生在支持下再做一次。"
        )

    misconceptions = obj.get("anticipated_misconceptions") if isinstance(obj.get("anticipated_misconceptions"), list) else []
    valid_mis = [x for x in misconceptions if isinstance(x, dict) and str(x.get("issue") or "").strip()]
    common_mis = _clean_str_list(obj.get("common_misconceptions"))
    if not valid_mis and common_mis:
        valid_mis = [{"issue": issue, "response": _mis_response(issue)} for issue in common_mis]
    if valid_mis:
        used = set()
        for item in valid_mis:
            issue = str(item.get("issue") or "").strip()
            resp = str(item.get("response") or "").strip()
            if not resp:
                resp = _mis_response(issue)
            if resp in used:
                resp = _mis_response(issue)
            used.add(resp)
            item["response"] = resp
    if not valid_mis:
        seeded = kp_items[:3] or (["概念混淆", "步骤遗漏"] if not is_en else ["Concept confusion", "Step omission"])
        valid_mis = [
            {
                "issue": issue,
                "response": _mis_response(issue),
            }
            for issue in seeded
        ]
    obj["anticipated_misconceptions"] = valid_mis

    # Assessment (map from thesis schema if needed)
    afl = obj.get("assessment_for_learning") if isinstance(obj.get("assessment_for_learning"), dict) else {}
    assessment = obj.get("assessment") if isinstance(obj.get("assessment"), dict) else {}
    hinge = assessment.get("hinge_question") if isinstance(assessment.get("hinge_question"), str) else ""
    exit_ticket = _clean_str_list(assessment.get("exit_ticket"))
    evidence = _clean_str_list(assessment.get("evidence_to_collect"))
    if hinge and (not isinstance(afl.get("informal_questioning"), str) or not afl.get("informal_questioning").strip()):
        afl["informal_questioning"] = hinge
    if exit_ticket and (not isinstance(afl.get("worksheet_evidence"), str) or not afl.get("worksheet_evidence").strip()):
        afl["worksheet_evidence"] = "; ".join(exit_ticket[:3])
    if evidence and (not isinstance(afl.get("observation"), str) or not afl.get("observation").strip()):
        afl["observation"] = "; ".join(evidence[:3])

    defaults_zh = {
        "informal_questioning": "课堂口头提问检核关键概念与易错点。",
        "live_visual_checks": "用小白板即时展示步骤，教师快速抽样纠错。",
        "observation": "巡视记录学生是否按步骤完成并及时提示。",
        "worksheet_evidence": "根据练习单正确率判断掌握情况并分层反馈。",
        "spoken_reasoning": "请学生口述为什么这样做。",
    }
    defaults_en = {
        "informal_questioning": "Use oral checks to probe key ideas and misconceptions.",
        "live_visual_checks": "Use mini-whiteboard snapshots for real-time correction.",
        "observation": "Circulate to record whether pupils follow the steps and prompt as needed.",
        "worksheet_evidence": "Use worksheet accuracy for tiered feedback.",
        "spoken_reasoning": "Ask pupils to explain their reasoning.",
    }
    defaults = defaults_en if is_en else defaults_zh
    for k, v in defaults.items():
        if not isinstance(afl.get(k), str) or not afl.get(k).strip():
            afl[k] = v
    obj["assessment_for_learning"] = afl

    # Steps / activities
    steps = obj.get("steps") if isinstance(obj.get("steps"), list) else []
    steps = [s for s in steps if isinstance(s, dict) and (str(s.get("title") or "").strip() or str(s.get("content") or "").strip())]
    if not steps:
        flow = obj.get("lesson_flow") if isinstance(obj.get("lesson_flow"), list) else []
        for step in flow:
            if not isinstance(step, dict):
                continue
            title = str(step.get("phase") or "").strip() or ("Step" if is_en else "环节")
            teacher_actions = _clean_str_list(step.get("teacher_actions"))
            pupil_actions = _clean_str_list(step.get("pupil_actions"))
            questions = _clean_str_list(step.get("questions"))
            checks = _clean_str_list(step.get("checking_for_understanding"))
            parts = []
            if teacher_actions:
                parts.append(("Teacher: " if is_en else "教师：") + " | ".join(teacher_actions))
            if pupil_actions:
                parts.append(("Pupil: " if is_en else "学生：") + " | ".join(pupil_actions))
            if questions:
                parts.append(("Questions: " if is_en else "提问：") + " | ".join(questions))
            if checks:
                parts.append(("Checks: " if is_en else "检核：") + " | ".join(checks))
            content = "\n".join(parts).strip()
            steps.append({"title": title, "content": content or ("Teacher-led modelling and pupil response." if is_en else "教师示范讲解，学生跟随练习。")})

    if not steps:
        base = topic or ("this topic" if is_en else "本课内容")
        if is_en:
            steps = [
                {"title": "Retrieval", "content": f"Teacher: recall prior learning and introduce {base}. Pupil: respond and share ideas."},
                {"title": "Input", "content": f"Teacher: model key concept of {base}. Pupil: observe and answer questions."},
                {"title": "Guided Practice", "content": "Teacher: guide example tasks. Pupil: practise with support."},
                {"title": "Independent Practice", "content": "Teacher: set short tasks. Pupil: practise independently and self-check."},
                {"title": "Plenary", "content": "Teacher: summarise and check understanding. Pupil: explain learning and next steps."},
            ]
        else:
            steps = [
                {"title": "导入", "content": f"教师：回顾旧知并引出{base}。学生：参与回答与交流。"},
                {"title": "新授", "content": f"教师：讲解并示范{base}核心方法。学生：观察、提问。"},
                {"title": "巩固练习", "content": "教师：带领完成示例。学生：跟随练习并纠错。"},
                {"title": "独立练习", "content": "教师：布置独立任务。学生：完成练习并自查。"},
                {"title": "总结", "content": "教师：总结要点并布置作业。学生：复述要点。"},
            ]
    if len(steps) < 5:
        base = topic or ("this topic" if is_en else "本课内容")
        defaults = [
            {"title": "Retrieval" if is_en else "导入", "content": f"Teacher: recall prior learning and introduce {base}." if is_en else f"教师：回顾旧知并引出{base}。"},
            {"title": "Input" if is_en else "新授", "content": f"Teacher: model the key concept of {base}." if is_en else f"教师：讲解并示范{base}核心方法。"},
            {"title": "Guided Practice" if is_en else "巩固练习", "content": "Teacher: guide example tasks." if is_en else "教师：带领完成示例。"},
            {"title": "Independent Practice" if is_en else "独立练习", "content": "Teacher: set short tasks for independent work." if is_en else "教师：布置独立任务。"},
            {"title": "Plenary" if is_en else "总结", "content": "Teacher: summarise and check understanding." if is_en else "教师：总结要点并检查理解。"},
        ]
        existing_titles = {str(x.get("title") or "").strip().lower() for x in steps if isinstance(x, dict)}
        for item in defaults:
            if len(steps) >= 5:
                break
            if str(item.get("title") or "").strip().lower() not in existing_titles:
                steps.append(item)
                existing_titles.add(str(item.get("title") or "").strip().lower())
    obj["steps"] = steps

    teaching_sequence = obj.get("teaching_sequence") if isinstance(obj.get("teaching_sequence"), list) else []
    if not teaching_sequence:
        obj["teaching_sequence"] = [
            {
                "phase": str(s.get("title") or "").strip(),
                "teacher_actions": [str(s.get("content") or "").strip()] if str(s.get("content") or "").strip() else [],
                "student_activities": [],
                "assessment_opportunities": [],
                "purpose": "",
                "duration_minutes": "",
            }
            for s in steps
            if isinstance(s, dict)
        ]

    if not isinstance(obj.get("activities"), list):
        obj["activities"] = [
            {"title": str(s.get("title") or ""), "content": str(s.get("content") or "")}
            for s in steps
            if isinstance(s, dict)
        ]

    # Exercises / homework
    exercises = obj.get("exercises") if isinstance(obj.get("exercises"), list) else []
    exercises = [x for x in exercises if isinstance(x, dict) and (str(x.get("question") or "").strip() or str(x.get("answer") or "").strip())]
    if not exercises:
        tasks = []
        practice = obj.get("practice_tasks") if isinstance(obj.get("practice_tasks"), dict) else {}
        for k in ["guided_practice", "independent_practice", "homework_optional"]:
            v = practice.get(k)
            if isinstance(v, list):
                tasks.extend([x for x in v if isinstance(x, dict)])
        for item in tasks:
            q = str(item.get("prompt") or item.get("task") or item.get("task_name") or item.get("question") or "").strip()
            a = str(item.get("expected_focus") or item.get("expected_answer") or item.get("answer") or item.get("success_indicator") or "").strip()
            if q:
                exercises.append({"question": q, "answer": a or ("Focus on key steps." if is_en else "关注关键步骤。")})

    if not exercises:
        base = topic or ("the lesson topic" if is_en else "本课内容")
        if is_en:
            exercises = [
                {"question": f"Explain a key idea from {base} in your own words.", "answer": "Clear explanation using key vocabulary."},
                {"question": f"Complete a basic example related to {base}.", "answer": "A correct worked example with steps shown."},
                {"question": f"Identify the correct method for {base} in a short task.", "answer": "Method identified and applied correctly."},
                {"question": f"Solve one guided practice problem about {base}.", "answer": "Correct final answer and method."},
                {"question": f"Solve one independent practice problem about {base}.", "answer": "Accurate answer with minimal errors."},
                {"question": f"Extension: apply {base} to a new context.", "answer": "Reasonable extension response."},
            ]
        else:
            exercises = [
                {"question": f"用自己的话说明{base}的关键要点。", "answer": "能用关键术语表述核心概念。"},
                {"question": f"完成一道与{base}相关的基础例题。", "answer": "步骤正确，结果正确。"},
                {"question": f"判断并选择解决{base}问题的正确方法。", "answer": "方法选择正确并说明理由。"},
                {"question": f"完成一题课堂跟练。", "answer": "过程完整且计算正确。"},
                {"question": f"完成一题独立练习。", "answer": "独立完成并自查纠错。"},
                {"question": f"拓展：在新情境中应用{base}。", "answer": "能合理迁移并给出解释。"},
            ]
    if len(exercises) < 6:
        base = topic or ("the lesson topic" if is_en else "本课内容")
        filler = [
            {"question": f"Explain a key idea from {base} in your own words.", "answer": "Clear explanation using key vocabulary."} if is_en else {"question": f"用自己的话说明{base}的关键要点。", "answer": "能用关键术语表述核心概念。"},
            {"question": f"Complete a basic example related to {base}.", "answer": "A correct worked example with steps shown."} if is_en else {"question": f"完成一道与{base}相关的基础例题。", "answer": "步骤正确，结果正确。"},
            {"question": f"Identify the correct method for {base} in a short task.", "answer": "Method identified and applied correctly."} if is_en else {"question": f"判断并选择解决{base}问题的正确方法。", "answer": "方法选择正确并说明理由。"},
            {"question": f"Solve one guided practice problem about {base}.", "answer": "Correct final answer and method."} if is_en else {"question": f"完成一题课堂跟练。", "answer": "过程完整且计算正确。"},
            {"question": f"Solve one independent practice problem about {base}.", "answer": "Accurate answer with minimal errors."} if is_en else {"question": f"完成一题独立练习。", "answer": "独立完成并自查纠错。"},
            {"question": f"Extension: apply {base} to a new context.", "answer": "Reasonable extension response."} if is_en else {"question": f"拓展：在新情境中应用{base}。", "answer": "能合理迁移并给出解释。"},
        ]
        existing_q = {str(x.get("question") or "").strip() for x in exercises if isinstance(x, dict)}
        for item in filler:
            if len(exercises) >= 6:
                break
            q = str(item.get("question") or "").strip()
            if q and q not in existing_q:
                exercises.append(item)
                existing_q.add(q)
    obj["exercises"] = exercises

    homework = obj.get("homework") if isinstance(obj.get("homework"), dict) else {}
    if not any(str(v).strip() for v in homework.values() if isinstance(v, str)):
        base = topic or ("the lesson topic" if is_en else "本课内容")
        homework = {
            "main_task": f"Complete core practice on {base}." if is_en else f"完成{base}相关基础练习。",
            "written_reflection": "Write one sentence about what you learned." if is_en else "写一句话总结本课所学。",
            "extension": f"Try one extension task on {base}." if is_en else f"尝试1道与{base}相关的拓展题。",
        }
    obj["homework"] = homework

    # Resources
    rs = obj.get("resources_summary") if isinstance(obj.get("resources_summary"), list) else []
    rs = [x for x in rs if isinstance(x, str) and x.strip()]
    if not rs:
        reps = obj.get("representations_and_resources") if isinstance(obj.get("representations_and_resources"), list) else []
        for item in reps:
            if not isinstance(item, dict):
                continue
            rep = str(item.get("representation") or "").strip()
            purpose = str(item.get("purpose") or "").strip()
            resource = str(item.get("resource") or "").strip()
            if rep:
                line = rep
                if resource:
                    line = f"{resource} - {rep}"
                if purpose:
                    line += f" ({purpose})"
                rs.append(line)
    if len(rs) < 3:
        defaults = [
            "小白板与记号笔" if not is_en else "Mini whiteboards and markers",
            "任务卡或学具" if not is_en else "Task cards or manipulatives",
            "分层练习单" if not is_en else "Tiered worksheets",
        ]
        for item in defaults:
            if item not in rs:
                rs.append(item)
    obj["resources_summary"] = rs

    ext = obj.get("external_resources") if isinstance(obj.get("external_resources"), list) else []
    ext = [x for x in ext if isinstance(x, dict)]
    meaningful = [
        x for x in ext
        if str(x.get("title") or "").strip() and str(x.get("description") or "").strip() and str(x.get("suggested_use") or "").strip()
    ]
    if not meaningful:
        obj["external_resources"] = [
            {
                "title": "教材配套讲解视频" if not is_en else "Curriculum-aligned explainer",
                "type": "video",
                "url": "",
                "description": "用于课后复习与巩固关键概念。" if not is_en else "Used for post-lesson review and consolidation.",
                "suggested_use": "课后复习 8-10 分钟。" if not is_en else "Use for 8-10 minute post-lesson review.",
            }
        ]

    return obj


def _build_lesson_title(grade: str, subject: str, topic: str, lang: str = "zh") -> str:
    g = (grade or "").strip()
    s = (subject or "").strip()
    t = (topic or "").strip()
    if (lang or "zh").lower() == "en":
        return f"{g} {s} {t} Lesson Plan".strip() or "Lesson Plan"
    if t.startswith("《") and t.endswith("》"):
        topic_part = t
    else:
        topic_part = f"《{t}》" if t else ""
    return f"{g}{s}{topic_part}教案".strip() or "教案"


def _sanitize_lesson_plan(raw: str, grade: str, subject: str, topic: str, lang: str = "zh") -> str:
    text = (raw or "").strip()
    if not text:
        return text

    # Remove markdown wrappers/noise.
    text = re.sub(r"^```(?:markdown|md|text)?\\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\\s*```$", "", text)
    text = text.replace("---", "")

    lines = [ln.rstrip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln.strip()]

    is_en = (lang or "zh").lower() == "en"
    title = _build_lesson_title(grade, subject, topic, lang=lang)
    start_idx = 0
    for i, ln in enumerate(lines):
        cur = ln.strip()
        if cur == title or re.match(r"^[一二三四五六七八九十]+、", cur) or re.match(r"^[IVX]+\.\s", cur, flags=re.IGNORECASE):
            start_idx = i
            break
    body_lines = lines[start_idx:] if lines else []

    cleaned = []
    ban_patterns = [
        r"^根据您提供的信息",
        r"^这是一份",
        r"^以下是",
        r"^教学设计好的",
        r"^《?教案》?",
        r"^based on the information you provided",
        r"^here is",
        r"^this is",
        r"^lesson plan",
    ]
    for ln in body_lines:
        cur = ln.strip().lstrip("#").strip()
        if any(re.search(p, cur) for p in ban_patterns):
            continue
        cleaned.append(cur)

    # Ensure top title exists in generated content for on-page preview/history consistency.
    if is_en:
        cleaned = [ln for ln in cleaned if ln.lower() != "teacher: [your name]"]

    if not cleaned or cleaned[0] != title:
        cleaned.insert(0, title)

    return "\\n".join(cleaned).strip()


WORKFLOW_STEP_NAMES = {
    1: "课标解读",
    2: "学情",
    3: "目标",
    4: "活动",
    5: "练习",
    6: "评价",
}


def _default_workflow_status() -> dict:
    return {f"step_{i}": "pending" for i in range(1, 7)}


def _coerce_json_dict(raw: str, default: dict) -> dict:
    obj = safe_json_loads(raw, default)
    return obj if isinstance(obj, dict) else default


def _ensure_workflow(user_id: int, workflow_id: int, topic: str, subject: str, grade: str):
    if workflow_id:
        wf = LessonWorkflow.query.get(int(workflow_id))
        if wf and int(wf.created_by) == int(user_id):
            return wf
        return None

    wf = LessonWorkflow(
        created_by=int(user_id),
        topic=topic,
        subject=subject,
        grade=grade,
        current_step=1,
        is_completed=False,
        status_json=json.dumps(_default_workflow_status(), ensure_ascii=False),
        content_json=json.dumps({}, ensure_ascii=False),
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now(),
    )
    db.session.add(wf)
    db.session.flush()
    return wf


def _check_workflow_step_dependency(workflow: LessonWorkflow, step_no: int) -> tuple[bool, str]:
    if not workflow:
        return False, "workflow not found"
    if step_no < 1 or step_no > 6:
        return False, "workflow_step 必须在 1-6"
    if step_no == 1:
        return True, ""

    status = _coerce_json_dict(workflow.status_json, _default_workflow_status())
    prev_key = f"step_{step_no - 1}"
    if status.get(prev_key) != "completed":
        prev_name = WORKFLOW_STEP_NAMES.get(step_no - 1, prev_key)
        return False, f"必须先完成前一步：{prev_name}"
    return True, ""


def _build_workflow_context(workflow: LessonWorkflow, current_step: int) -> str:
    if not workflow:
        return ""
    content = _coerce_json_dict(workflow.content_json, {})
    parts = []
    for i in range(1, current_step):
        val = content.get(f"step_{i}")
        if isinstance(val, str) and val.strip():
            step_name = WORKFLOW_STEP_NAMES.get(i, f"step_{i}")
            parts.append(f"[{step_name}]\n{val.strip()}")
    if not parts:
        return ""
    return "\n\n【前序步骤上下文（生成当前步骤时必须继承）】\n" + "\n\n".join(parts) + "\n"


def _update_workflow_after_generation(workflow: LessonWorkflow, step_no: int, content: str, status_value: str):
    if not workflow:
        return
    status = _coerce_json_dict(workflow.status_json, _default_workflow_status())
    content_map = _coerce_json_dict(workflow.content_json, {})
    status[f"step_{step_no}"] = status_value
    content_map[f"step_{step_no}"] = content
    workflow.status_json = json.dumps(status, ensure_ascii=False)
    workflow.content_json = json.dumps(content_map, ensure_ascii=False)
    if status_value == "completed":
        workflow.current_step = min(6, int(step_no) + 1)
    workflow.is_completed = all(status.get(f"step_{i}") == "completed" for i in range(1, 7))
    workflow.updated_at = datetime.datetime.now()


def _build_need_review_template(
    lesson_title: str,
    grade: str,
    subject: str,
    topic: str,
    reasons: list,
    lang: str = "zh",
):
    is_en = (lang or "zh").lower() == "en"
    template = {
        "title": lesson_title,
        "objectives": [],
        "steps": [],
        "exercises": [],
        "_meta": {
            "status": "need_review",
            "reason": reasons,
            "grade": grade,
            "subject": subject,
            "topic": topic,
            "message": "Manual review required" if is_en else "需人工复核",
        },
    }
    return _ensure_display_completeness(template, key_points="", lang=lang)


def _clean_json_with_llm(raw_text: str) -> str:
    prompt = (
        "You are a JSON repair assistant.\n"
        "Return one valid JSON object only.\n"
        "Do not output markdown, explanation, or extra text.\n"
        "If there are trailing comments or wrappers, remove them.\n"
        "Input text:\n"
        f"{raw_text}"
    )
    return ai_service.generate_lesson_text(prompt, max_completion_tokens=4000)


def _create_generation_log(
    created_by: int,
    workflow_id: int,
    lesson_id: int,
    step_no: int,
    parse_status: str,
    validation_status: str,
    math_status: str,
    failure_reason: str,
    raw_output: str,
    extracted_output,
    need_review: bool,
):
    try:
        log = GenerationLog(
            created_by=int(created_by),
            workflow_id=workflow_id,
            lesson_id=lesson_id,
            step_no=step_no,
            parse_status=parse_status,
            validation_status=validation_status,
            math_status=math_status,
            failure_reason=failure_reason,
            raw_output=raw_output,
            extracted_output=(
                json.dumps(extracted_output, ensure_ascii=False, indent=2)
                if isinstance(extracted_output, (dict, list))
                else (str(extracted_output) if extracted_output is not None else None)
            ),
            need_review=bool(need_review),
            created_at=datetime.datetime.now(),
        )
        db.session.add(log)
    except Exception:
        # Keep main generation path resilient.
        pass


def _create_validation_log(
    created_by: int,
    entity_type: str,
    entity_id: int,
    workflow_id: int,
    step_no: int,
    parse_status: str,
    validation_status: str,
    need_review: bool,
    reasons: list,
):
    try:
        row = ValidationLog(
            created_by=int(created_by),
            entity_type=entity_type,
            entity_id=entity_id,
            workflow_id=workflow_id,
            step_no=step_no,
            parse_status=(parse_status or "unknown"),
            validation_status=(validation_status or "unknown"),
            need_review=bool(need_review),
            reasons_json=json.dumps(reasons or [], ensure_ascii=False),
            review_reason=("; ".join([str(x) for x in (reasons or [])])[:1000] if reasons else None),
            created_at=datetime.datetime.now(),
        )
        db.session.add(row)
    except Exception:
        pass


def _compute_text_diff(before_text: str, after_text: str) -> dict:
    before_lines = (before_text or "").splitlines()
    after_lines = (after_text or "").splitlines()
    unified = list(
        difflib.unified_diff(
            before_lines,
            after_lines,
            fromfile="before",
            tofile="after",
            lineterm="",
        )
    )
    return {
        "changed": bool((before_text or "") != (after_text or "")),
        "line_diff": unified,
    }


def _extract_meta_from_description(description: str) -> dict:
    desc = description or ""
    if not isinstance(desc, str) or not desc.startswith("__META__"):
        return {}
    try:
        meta_str, _ = desc.split("__\n", 1)
        meta = json.loads(meta_str.replace("__META__", ""))
        return meta if isinstance(meta, dict) else {}
    except Exception:
        return {}


def _topic_related(target_topic: str, exercise: Exercise) -> bool:
    t = (target_topic or "").strip().lower()
    if not t:
        return True
    title = (exercise.title or "").strip().lower() if exercise else ""
    if t in title:
        return True
    meta = _extract_meta_from_description(exercise.description or "") if exercise else {}
    meta_topic = str(meta.get("topic") or "").strip().lower() if isinstance(meta, dict) else ""
    return bool(meta_topic and t in meta_topic)


def _load_json_obj(raw: str, default):
    try:
        value = json.loads(raw or "")
        return value if isinstance(value, type(default)) else default
    except Exception:
        return default


def _build_student_learning_diagnosis(created_by: int, class_id: int, topic: str, lang: str = "zh") -> dict:
    pubs_q = ResourcePublish.query.filter_by(created_by=int(created_by), revoked=False, resource_type="exercise")
    if class_id:
        pubs_q = pubs_q.filter_by(class_id=int(class_id))
    pubs = pubs_q.order_by(ResourcePublish.created_at.desc()).limit(40).all()
    if not pubs:
        return {
            "completion_rate": 0,
            "avg_score": None,
            "graded_count": 0,
            "common_misconceptions": [],
            "weak_question_types": [],
            "summary": "No assignment data available yet." if lang == "en" else "暂无作业数据，可先发布诊断练习后再生成学情。",
        }

    pub_ids = [p.id for p in pubs]
    exercise_ids = list({p.resource_id for p in pubs})
    exercises = {e.id: e for e in Exercise.query.filter(Exercise.id.in_(exercise_ids)).all()} if exercise_ids else {}

    matched_pubs = []
    for p in pubs:
        ex = exercises.get(p.resource_id)
        if ex and _topic_related(topic, ex):
            matched_pubs.append(p)
    if not matched_pubs:
        matched_pubs = pubs[:10]

    matched_pub_ids = [p.id for p in matched_pubs]
    assignments = ResourceAssignment.query.filter(ResourceAssignment.publish_id.in_(matched_pub_ids)).all() if matched_pub_ids else []
    submissions = ExerciseSubmission.query.filter(ExerciseSubmission.publish_id.in_(matched_pub_ids)).all() if matched_pub_ids else []

    assigned = len(assignments)
    completed = len([a for a in assignments if a.status == "completed"])
    completion_rate = round((completed / assigned) * 100, 1) if assigned else 0

    graded_subs = [s for s in submissions if s.status == "graded" and s.total_score is not None]
    avg_score = round(sum([int(s.total_score or 0) for s in graded_subs]) / len(graded_subs), 1) if graded_subs else None

    wrong_by_type = {}
    total_by_type = {}
    misconception_counter = {}

    for s in submissions:
        ex_pub = None
        for p in matched_pubs:
            if p.id == s.publish_id:
                ex_pub = p
                break
        if not ex_pub:
            continue
        ex = exercises.get(ex_pub.resource_id)
        if not ex or not ex.content_json:
            continue
        structured = _load_json_obj(ex.content_json, {})
        auto_result = _load_json_obj(s.auto_result, {})
        teacher_detail = _load_json_obj(s.teacher_detail, {})
        questions = structured.get("questions") if isinstance(structured.get("questions"), list) else []

        for q in questions:
            qid = q.get("id")
            qtype = str(q.get("type") or "unknown").lower()
            if not qid:
                continue
            total_by_type[qtype] = total_by_type.get(qtype, 0) + 1

            is_wrong = False
            if qtype in ("short", "essay"):
                detail = teacher_detail.get(qid) if isinstance(teacher_detail.get(qid), dict) else {}
                if detail:
                    max_score = int(q.get("score") or 0)
                    got = int(detail.get("score") or 0)
                    is_wrong = got < max_score
            else:
                is_wrong = auto_result.get(qid) == "wrong"

            if is_wrong:
                wrong_by_type[qtype] = wrong_by_type.get(qtype, 0) + 1
                stem = str(q.get("stem") or "").strip()
                if stem:
                    key = stem[:60]
                    misconception_counter[key] = misconception_counter.get(key, 0) + 1

    weak_types = []
    for k, total in total_by_type.items():
        wrong = wrong_by_type.get(k, 0)
        if total > 0:
            weak_types.append((k, round((wrong / total) * 100, 1), total))
    weak_types.sort(key=lambda x: x[1], reverse=True)
    weak_question_types = [f"{x[0]}({x[1]}%)" for x in weak_types[:3]]

    sorted_mis = sorted(misconception_counter.items(), key=lambda x: x[1], reverse=True)
    common_misconceptions = [x[0] for x in sorted_mis[:3]]

    if lang == "en":
        summary = (
            f"Homework analysis: completion rate {completion_rate}%, "
            f"graded samples {len(graded_subs)}, average score {avg_score if avg_score is not None else '-'}; "
            f"common misconceptions: {common_misconceptions or ['not enough evidence']}; "
            f"weak question types: {weak_question_types or ['not enough evidence']}."
        )
    else:
        summary = (
            f"作业学情：完成率{completion_rate}%，已批改样本{len(graded_subs)}份，"
            f"平均分{avg_score if avg_score is not None else '暂无'}；"
            f"常见误区：{common_misconceptions or ['证据不足']}；"
            f"薄弱题型：{weak_question_types or ['证据不足']}。"
        )

    return {
        "completion_rate": completion_rate,
        "avg_score": avg_score,
        "graded_count": len(graded_subs),
        "common_misconceptions": common_misconceptions,
        "weak_question_types": weak_question_types,
        "summary": summary,
    }


def _build_iteration_seed_from_workflow(workflow: LessonWorkflow, class_diagnosis: dict, lang: str = "zh") -> str:
    content_map = _coerce_json_dict(workflow.content_json, {})
    step3 = str(content_map.get("step_3") or "").strip()
    step5 = str(content_map.get("step_5") or "").strip()
    step6 = str(content_map.get("step_6") or "").strip()

    completion_rate = class_diagnosis.get("completion_rate")
    avg_score = class_diagnosis.get("avg_score")
    weak_types = class_diagnosis.get("weak_question_types") or []
    misconceptions = class_diagnosis.get("common_misconceptions") or []

    if lang == "en":
        return (
            f"Curriculum re-analysis seed for next cycle:\n"
            f"- Previous objectives/key challenges summary: {step3[:500] if step3 else 'N/A'}\n"
            f"- Previous differentiated exercise summary: {step5[:500] if step5 else 'N/A'}\n"
            f"- Post-lesson evaluation summary: {step6[:500] if step6 else 'N/A'}\n"
            f"- Response data signals: completion_rate={completion_rate}%, avg_score={avg_score}, weak_types={weak_types}, misconceptions={misconceptions}\n"
            f"- Required next-cycle focus: refine key concept sequencing, reduce misconception hotspots, and redesign support/core/stretch tasks."
        )
    return (
        f"下一轮课标再分析种子：\n"
        f"- 上一轮目标与重难点摘要：{step3[:500] if step3 else '暂无'}\n"
        f"- 上一轮分层练习摘要：{step5[:500] if step5 else '暂无'}\n"
        f"- 课后评价摘要：{step6[:500] if step6 else '暂无'}\n"
        f"- 学生响应数据：完成率={completion_rate}%，平均分={avg_score}，薄弱题型={weak_types}，共性误区={misconceptions}\n"
        f"- 下一轮要求：回到课标重新拆解关键概念，针对高频误区重排教学顺序，并重设计support/core/stretch分层任务。"
    )


def _safe_json_list(raw: str) -> list:
    try:
        value = json.loads(raw or "")
        return value if isinstance(value, list) else []
    except Exception:
        return []


def _build_review_feedback_context(created_by: int, class_id: int, topic: str, lang: str = "zh") -> dict:
    rows_q = AssignmentAnalysis.query.filter_by(created_by=int(created_by))
    if class_id:
        rows_q = rows_q.filter_by(class_id=int(class_id))
    rows = rows_q.order_by(AssignmentAnalysis.updated_at.desc()).limit(80).all()

    if not rows:
        return {"count": 0, "context": ""}

    matched = []
    for row in rows:
        stub = type("_StubExercise", (), {})()
        stub.title = row.title or ""
        stub.description = ""
        if _topic_related(topic, stub):
            matched.append(row)

    if not matched:
        matched = rows[:8]
    else:
        matched = matched[:8]

    if not matched:
        return {"count": 0, "context": ""}

    lines = []
    for idx, row in enumerate(matched, start=1):
        weak_types = _safe_json_list(row.weak_question_types_json)
        misconceptions = _safe_json_list(row.common_misconceptions_json)

        score_text = "-"
        if row.score is not None and row.max_score:
            score_text = f"{row.score}/{row.max_score}"
        elif row.score is not None:
            score_text = str(row.score)

        if lang == "en":
            lines.append(
                f"{idx}. title={row.title or '-'}; score={score_text}; completion={row.completion_rate if row.completion_rate is not None else '-'}%; weak_types={weak_types or ['n/a']}; misconceptions={misconceptions or ['n/a']}; teacher_note={(row.summary_text or '')[:180]}"
            )
        else:
            lines.append(
                f"{idx}. 标题={row.title or '-'}；得分={score_text}；完成率={row.completion_rate if row.completion_rate is not None else '-'}%；薄弱题型={weak_types or ['暂无']}；共性误区={misconceptions or ['暂无']}；教师反馈摘要={(row.summary_text or '')[:180]}"
            )

    if lang == "en":
        context = (
            "\n\n[Review-mode historical learning feedback]\n"
            "This lesson is a REVIEW LESSON. The teacher enabled review mode.\n"
            "You must use these assignment analyses for same/similar topic and reflect them in objectives, pacing, and differentiated tasks.\n"
            + "\n".join(lines)
            + "\nRequired: explicitly map remediation actions to students' wrong-question patterns, weak question types, and common misconceptions.\n"
        )
    else:
        context = (
            "\n\n【复习模式历史学情反馈】\n"
            "本节课是复习课。教师已勾选复习，必须吸收下列同课题/近似课题作业分析，并在教学目标、节奏与分层任务中显式体现。\n"
            + "\n".join(lines)
            + "\n要求：必须围绕学生已做过的错题模式、薄弱题型、共性误区，给出一一对应的纠偏动作与巩固练习。\n"
        )

    return {"count": len(matched), "context": context}


@bp.route("/generate", methods=["POST", "OPTIONS"])
@token_required
def generate_lesson():
    if request.method == "OPTIONS":
        return "", 204

    data = request.get_json(silent=True) or {}
    grade = data.get("grade", "")
    subject = data.get("subject", "")
    topic = data.get("topic", "")
    duration = data.get("duration", "")
    lesson_count = data.get("lesson_count", "")
    session_index_raw = data.get("session_index", 0)
    session_total_raw = data.get("session_total", 0)
    session_focus = str(data.get("session_focus") or data.get("progressive_focus") or "").strip()
    source_topic = str(data.get("source_topic") or "").strip()
    lang = (data.get("lang") or "zh").strip().lower()
    objectives = data.get("objectives", "")
    key_points = data.get("key_points", "")
    activities = data.get("activities", "")
    output_format = str(data.get("output_format", data.get("response_format", "json")) or "json").strip().lower()
    json_only = bool(data.get("json_only", False))
    json_schema = data.get("json_schema") if isinstance(data.get("json_schema"), dict) else None
    required_json_fields = data.get("required_json_fields") if isinstance(data.get("required_json_fields"), list) else None
    want_json = (output_format != "text") or json_only or json_schema is not None
    strict_example_structure = bool(data.get("strict_example_structure", True)) if want_json else False
    requested_max_tokens = data.get("max_completion_tokens", None)
    math_rule_mode = bool(data.get("math_rule_mode", False))
    is_math_subject = str(subject or "").strip().lower() in ("数学", "math")
    use_knowledge_retrieval = bool(data.get("use_knowledge_retrieval", True if is_math_subject else math_rule_mode))
    use_custom_knowledge_base = bool(data.get("use_custom_knowledge_base", True))
    use_symbolic_verification = bool(data.get("use_symbolic_verification", math_rule_mode))
    include_tool_generated_examples = bool(data.get("include_tool_generated_examples", False))
    include_geometry_figure = bool(data.get("include_geometry_figure", False))
    math_difficulty = str(data.get("math_difficulty", "basic") or "basic").strip().lower()
    workflow_id = int(data.get("workflow_id") or 0)
    workflow_step = int(data.get("workflow_step") or 1)
    class_id = int(data.get("class_id") or 0)
    include_review_feedback = bool(data.get("include_review_feedback", False))
    jurisdiction = str(data.get("jurisdiction") or "").strip()
    locale = str(data.get("locale") or "").strip()
    thesis_mode = data.get("thesis_mode")

    if not topic:
        return err("topic is required", http_status=400)

    try:
        session_index = int(session_index_raw or 0)
    except Exception:
        session_index = 0
    try:
        session_total = int(session_total_raw or 0)
    except Exception:
        session_total = 0

    if session_total <= 0:
        try:
            session_total = max(1, int(lesson_count or 1))
        except Exception:
            session_total = 1
    if session_index <= 0:
        session_index = 1
    if session_index > session_total:
        session_index = session_total

    if thesis_mode is None:
        thesis_mode = bool(lang == "en" or jurisdiction.lower() == "england" or locale.lower() == "en-gb")
    else:
        thesis_mode = bool(thesis_mode)

    year_group = _normalize_year_group(grade)
    inferred_key_stage = _infer_key_stage(year_group)

    retrieval_context_block = ""
    retrieved_knowledge = {}
    tooling_bundle = None

    if math_rule_mode:
        want_json = True
        strict_example_structure = False
        if required_json_fields is None:
            required_json_fields = ["title", "objectives", "steps", "exercises", "prerequisite_knowledge", "core_formula", "example_chain"]
        if use_knowledge_retrieval:
            retrieval_context_block = build_retrieval_context_block(topic, lang=lang)
            retrieved_knowledge = retrieve_math_knowledge(topic)
        if include_tool_generated_examples:
            tooling_bundle = generate_math_tooling_bundle(
                topic=topic,
                difficulty=math_difficulty,
                include_geometry=include_geometry_figure,
            )

    lesson_title = _build_lesson_title(grade, subject, topic, lang=lang)
    created_by = int(getattr(g, "current_user_id", 0) or 0)

    prompt_json_zh = f"""
你是一名小学数学教案编写专家。
请只输出一个 JSON 对象，不要输出任何解释或 Markdown 代码块。

输入信息：
- 年级：{grade}
- 学科：{subject}
- 课题：{topic}
- 课时：{duration} 分钟
- 节数：{lesson_count}
- 教学目标：{objectives}
- 重难点：{key_points}
- 教学活动：{activities}

必须输出字段（严格）：
- title: string
- objectives: string[]
- steps: [{{"title": string, "content": string}}]
- exercises: [{{"question": string, "answer": string}}]
- anticipated_misconceptions: [{{"issue": string, "response": string}}]
- assessment_for_learning: object（含提问/观察/练习证据等）
- resources_summary: string[]
- external_resources: [{{"title": string, "description": string, "suggested_use": string}}]

硬性要求：
1) 顶层必须是 JSON 对象。
2) 不允许返回 JSON 之外的文本。
3) objectives 至少 3 条；steps 至少 5 条；exercises 至少 6 条。
4) 禁止输出“暂无/N/A/待补充”等占位词，所有字段需给出具体可用内容。
5) 纠正策略必须具体：每条 anticipated_misconceptions 的 response 要写清教师话术、操作步骤与示例对比，不允许泛泛“及时反馈”。
6) 活动梯度必须完整：teacher-led → paired → guided individual → independent；在 guided_practice 中加入“示范-跟做-独立尝试”的交接环节。
7) 评价与目标对齐：每条目标必须对应至少一条 assessment_for_learning，含口头表达目标时必须有口头检查。
8) 作业/练习答案必须具体，不得写“见标准/see success criteria”。
9) 若课题涉及零/0/zero，必须包含“先有-再空”的认知冲突活动与教师追问。
10) 资源需包含数量、使用时机与替代方案（如学具不足时）。
"""

    prompt_json_en = f"""
You are an expert K-12 lesson plan writer.
Return one JSON object only. No markdown code block. No extra text.

Input:
- Grade: {grade}
- Subject: {subject}
- Topic: {topic}
- Duration: {duration} minutes
- Lesson count: {lesson_count}
- Objectives: {objectives}
- Key points: {key_points}
- Activities: {activities}

Required output fields:
- title: string
- objectives: string[]
- steps: [{{"title": string, "content": string}}]
- exercises: [{{"question": string, "answer": string}}]
- anticipated_misconceptions: [{{"issue": string, "response": string}}]
- assessment_for_learning: object
- resources_summary: string[]
- external_resources: [{{"title": string, "description": string, "suggested_use": string}}]

Hard requirements:
1) Top-level value must be a JSON object.
2) No text outside JSON.
3) At least 3 objectives, 5 steps, and 6 exercises.
4) Do not use placeholders like N/A or "to be completed"; provide concrete content for all fields.
5) Misconception responses must be concrete: include teacher talk, actions, and a worked contrast (not generic "use feedback").
6) Activity gradient must be explicit: teacher-led → paired → guided individual → independent; include a handover in guided practice.
7) Assessment must align to objectives; if an objective is about speaking, include a speaking check.
8) Exercise/homework answers must be specific; do not write "see success criteria".
9) If the topic involves zero/0, include a cognitive-conflict activity (e.g., remove items to none) with teacher prompts.
10) Resources must state quantity, lesson timing, and alternatives if unavailable.
"""

    prompt_text_zh = f"""
你是一名小学数学教案编写专家。请输出可直接上课使用的完整教案正文（纯文本，不要 Markdown 代码块）。

输入信息：
- 年级：{grade}
- 学科：{subject}
- 课题：{topic}
- 课时：{duration} 分钟
- 节数：{lesson_count}
- 教学目标：{objectives}
- 重难点：{key_points}
- 教学活动：{activities}

必须包含并写充实以下部分：
1) 教学目标（至少3条）
2) 重难点（至少2条，含应对策略）
3) 教学过程（至少5个环节，写清教师活动、学生活动、时间）
4) 评价与反馈（至少3条可操作做法）
5) 作业设计（至少6题，含答案）
6) 教学资源展示（至少3项）
7) 禁止使用“暂无/N/A/待补充”等占位词。
8) 纠正策略需具体化：给出教师话术、操作步骤、对比例题。
9) 活动梯度需包含“示范-跟做-独立尝试”过渡。
10) 评价必须与目标一一对应；涉及口头表达的目标必须设计口头检查。
11) 若涉及零/0/zero，必须设计“先有后空”的认知冲突活动与追问语言。
12) 资源需说明数量、使用时机与替代方案。
"""

    prompt_text_en = f"""
You are an expert primary-math lesson planner. Return classroom-ready lesson text only (no markdown code block).

Input:
- Grade: {grade}
- Subject: {subject}
- Topic: {topic}
- Duration: {duration} minutes
- Lesson count: {lesson_count}
- Objectives: {objectives}
- Key points: {key_points}
- Activities: {activities}

Must include and fully develop:
1) Objectives (>=3)
2) Key and difficult points (>=2 with teaching responses)
3) Teaching process (>=5 phases with teacher/pupil actions and timing)
4) Assessment and feedback (>=3 actionable methods)
5) Homework (>=6 items with answers)
6) Teaching resources (>=3 items)
7) Do not use placeholders such as N/A or "to be completed".
8) Misconception responses must include teacher talk, actions, and worked contrasts.
9) Include a handover sequence from modelled to supported to independent.
10) Assessments must align to each objective; speaking objectives require speaking checks.
11) If zero/0 is involved, include a cognitive-conflict activity with teacher prompts.
12) Resources must specify quantity, timing, and alternatives.
"""

    required_fields = required_json_fields or _default_lesson_json_required_fields(lang=lang)
    uk_guardrails = None
    if thesis_mode and want_json:
        uk_guardrails = _load_uk_guardrails()
        if not json_schema:
            json_schema = _load_uk_lesson_schema()
        if required_json_fields is None:
            required_fields = list((json_schema or {}).get("required") or [])

        hard_rules = (uk_guardrails.get("hard_rules") or {}) if isinstance(uk_guardrails, dict) else {}
        prompt_json_en += (
            "\n\nUK dissertation guardrails (mandatory):\n"
            "- Teacher-facing output only; no unsupervised child tutoring.\n"
            "- Teacher review is required before classroom release.\n"
            "- Return JSON only and follow schema exactly.\n"
            "- Use British English and avoid Americanisms.\n"
            "- Do not request pupil personal data.\n"
            "- Do not invent curriculum references.\n"
            "- If inputs are missing, include explicit assumptions.\n"
        )
        prompt_json_en += (
            f"\nJurisdiction: England\n"
            f"Locale: en-GB\n"
            f"Year group: {year_group or grade}\n"
            f"Key stage: {inferred_key_stage}\n"
            f"Teacher review required: {str(hard_rules.get('teacher_review_required', True)).lower()}\n"
        )

    if required_json_fields is None:
        prompt_json_zh += f"\n必须包含字段：{json.dumps(required_fields, ensure_ascii=False)}\n"
        prompt_json_en += f"\nRequired fields: {json.dumps(required_fields, ensure_ascii=False)}\n"

    if json_schema:
        schema_text = json.dumps(json_schema, ensure_ascii=False, indent=2)
        prompt_json_zh += f"\n请严格遵循以下 JSON Schema：\n{schema_text}\n"
        prompt_json_en += f"\nYou must strictly follow this JSON schema:\n{schema_text}\n"

    if math_rule_mode:
        prompt_json_zh += (
            "\n数学规则层要求（必须满足）：\n"
            "1) prerequisite_knowledge 必须是数组。\n"
            "2) core_formula 必须包含 latex 与 constraints。\n"
            "3) example_chain 每个对象必须包含 type/question/answer/verification_method。\n"
            "4) 题目与答案必须可自动校验一致。\n"
        )
        prompt_json_en += (
            "\nMath rule-layer constraints:\n"
            "1) prerequisite_knowledge should be an array.\n"
            "2) core_formula must include latex and constraints.\n"
            "3) example_chain items must include type/question/answer/verification_method.\n"
            "4) Question-answer pairs must pass automatic consistency checks.\n"
        )
        if retrieval_context_block:
            prompt_json_zh += f"\n{retrieval_context_block}\n"
            prompt_json_en += f"\n{retrieval_context_block}\n"
        if isinstance(tooling_bundle, dict):
            prompt_json_zh += f"\n可参考工具验证结果：\n{json.dumps(tooling_bundle, ensure_ascii=False, indent=2)}\n"
            prompt_json_en += f"\nTool-verified assets:\n{json.dumps(tooling_bundle, ensure_ascii=False, indent=2)}\n"

    prompt = (prompt_json_en if lang == "en" else prompt_json_zh) if want_json else (prompt_text_en if lang == "en" else prompt_text_zh)

    if session_total > 1:
        normalized_topic = source_topic or topic
        if lang == "en":
            progressive_block = (
                "\n\n[Multi-session progressive generation constraints]\n"
                f"- This is lesson {session_index}/{session_total} for the same topic: {normalized_topic}.\n"
                "- Keep topic identity unchanged; do not rename it into another topic title.\n"
                "- Design this lesson as part of a progressive sequence from easier to deeper understanding.\n"
                "- Ensure continuity with previous lessons and preview next lesson bridge.\n"
            )
            if session_focus:
                progressive_block += f"- Current lesson focus: {session_focus}.\n"
            if session_index == 1:
                progressive_block += "- Emphasize concept entry, baseline checks, and key vocabulary.\n"
            elif session_index == session_total:
                progressive_block += "- Emphasize transfer, integrated practice, and summative check.\n"
            else:
                progressive_block += "- Emphasize method consolidation, error correction, and scaffolded advancement.\n"
        else:
            progressive_block = (
                "\n\n【多课时递进生成约束】\n"
                f"- 当前是同一课题《{normalized_topic}》的第 {session_index}/{session_total} 节。\n"
                "- 课题名称必须保持一致，不要改写成新的课题名。\n"
                "- 内容必须体现由浅入深、循序渐进，并与前后课时形成衔接。\n"
                "- 需明确本节与上一节的承接点、与下一节的铺垫点。\n"
            )
            if session_focus:
                progressive_block += f"- 本节聚焦：{session_focus}。\n"
            if session_index == 1:
                progressive_block += "- 首节重点：概念建立、诊断性起点、核心术语统一。\n"
            elif session_index == session_total:
                progressive_block += "- 末节重点：综合迁移、易错纠偏、阶段性达成检核。\n"
            else:
                progressive_block += "- 中间课时重点：方法建构、分层练习、错误模式修正。\n"
        prompt += progressive_block

    parse_status = "not_required"
    validation_status = "not_required"
    math_status = "not_required"
    need_review = False
    review_reasons = []
    lesson_plan_json = None
    lesson_plan_raw = ""
    math_validation_errors = []
    workflow = None
    class_diagnosis = None
    review_feedback_count = 0

    try:
        if not Config.OPENAI_API_KEY:
            return err("OpenAI API key not configured", http_status=500)

        workflow = _ensure_workflow(created_by, workflow_id, topic, subject, grade)
        if workflow is None:
            return err("workflow not found", http_status=404)
        ok_dep, dep_msg = _check_workflow_step_dependency(workflow, workflow_step)
        if not ok_dep:
            return err(dep_msg, http_status=409)

        workflow_ctx = _build_workflow_context(workflow, workflow_step)
        if workflow_ctx and want_json:
            prompt += workflow_ctx

        if use_knowledge_retrieval and workflow_step in (1, 5):
            retrieval_context_block = retrieval_context_block or build_retrieval_context_block(topic, lang=lang)
            if isinstance(retrieved_knowledge, dict) and not retrieved_knowledge:
                retrieved_knowledge = retrieve_math_knowledge(topic)
            if retrieval_context_block:
                if lang == "en":
                    prompt += (
                        "\n\n[Knowledge-base injection for curriculum and misconceptions]\n"
                        "Use this curated curriculum snippet and common misconception set as hard context.\n"
                        f"{retrieval_context_block}\n"
                    )
                else:
                    prompt += (
                        "\n\n【知识库注入：课标与常见错因】\n"
                        "请将以下人工整理的课标条目与常见错因作为前置上下文吸收。\n"
                        f"{retrieval_context_block}\n"
                    )

        if include_review_feedback:
            review_feedback = _build_review_feedback_context(
                created_by=created_by,
                class_id=class_id,
                topic=topic,
                lang=lang,
            )
            review_feedback_count = int(review_feedback.get("count") or 0)
            if lang == "en":
                prompt += (
                    "\n\n[Review lesson hard requirement]\n"
                    "This generation is for a review lesson.\n"
                    "You must prioritize remediation and consolidation based on students' past wrong answers and misconception hotspots, not generic new-teaching flow.\n"
                )
            else:
                prompt += (
                    "\n\n【复习课硬性要求】\n"
                    "本次生成为复习课。\n"
                    "必须优先围绕学生历史错题与易错知识点进行纠偏与巩固，而不是通用新授流程。\n"
                )
            prompt += str(review_feedback.get("context") or "")

        if use_custom_knowledge_base:
            custom_kb_context = build_knowledge_injection_context(
                created_by=created_by,
                topic=topic,
                class_id=class_id or None,
                lang=lang,
                limit=8,
            )
            if custom_kb_context:
                if lang == "en":
                    prompt += (
                        "\n\n[Custom user knowledge base]\n"
                        "Apply the following user-imported knowledge as grounding context.\n"
                        f"{custom_kb_context}\n"
                    )
                else:
                    prompt += (
                        "\n\n【用户知识库注入】\n"
                        "请将以下用户导入的知识库内容作为强约束上下文。\n"
                        f"{custom_kb_context}\n"
                    )

        # Map to dissertation flow:
        # 1 curriculum analysis -> 2 diagnosis -> 3 objectives/key challenges
        # -> 4 activity design -> 5 differentiated exercises -> 6 post-lesson evaluation/iteration.
        if workflow_step == 2:
            class_diagnosis = _build_student_learning_diagnosis(
                created_by=created_by,
                class_id=class_id,
                topic=topic,
                lang=lang,
            )
            diagnosis_json = json.dumps(class_diagnosis, ensure_ascii=False, indent=2)
            if lang == "en":
                prompt += (
                    "\n\n[Step-2 Student Learning Diagnosis Required]\n"
                    "Use homework response data to diagnose learning status and misconceptions.\n"
                    "Output must include explicit learning_summary derived from evidence.\n"
                    f"Evidence:\n{diagnosis_json}\n"
                )
            else:
                prompt += (
                    "\n\n【第2步 学情诊断】\n"
                    "必须基于作业响应数据输出学情诊断与共性误区，并形成 learning_summary。\n"
                    f"证据数据：\n{diagnosis_json}\n"
                )

        if workflow_step == 3:
            if lang == "en":
                prompt += (
                    "\n\n[Step-3 Objectives and Key Challenges]\n"
                    "Transform curriculum analysis + learning diagnosis into lesson objectives and key/difficult points.\n"
                    "Make objective statements measurable and traceable to misconceptions.\n"
                )
            else:
                prompt += (
                    "\n\n【第3步 学习目标与重难点】\n"
                    "必须把前序课标解读与学情诊断转化为可测量教学目标，并明确重难点与误区对应关系。\n"
                )

        if workflow_step == 5:
            if lang == "en":
                prompt += (
                    "\n\n[Step-5 Worked Examples and Differentiated Exercises]\n"
                    "Design support/core/stretch (three-level) exercises.\n"
                    "Each level must explicitly reference key/difficult points from Step-3.\n"
                )
            else:
                prompt += (
                    "\n\n【第5步 例题与分层练习】\n"
                    "必须输出 support/core/stretch 三层练习设计，并逐项对应第3步的重难点。\n"
                )

        if workflow_step == 6:
            class_diagnosis = class_diagnosis or _build_student_learning_diagnosis(
                created_by=created_by,
                class_id=class_id,
                topic=topic,
                lang=lang,
            )
            diagnosis_json = json.dumps(class_diagnosis, ensure_ascii=False, indent=2)
            if lang == "en":
                prompt += (
                    "\n\n[Step-6 Post-Lesson Evaluation and Iteration]\n"
                    "Analyze response data and generate iterative teaching feedback.\n"
                    "Must include: response data analysis, learning feedback, and next-cycle curriculum re-analysis trigger.\n"
                    f"Response evidence:\n{diagnosis_json}\n"
                )
            else:
                prompt += (
                    "\n\n【第6步 课后评价与迭代】\n"
                    "必须基于响应数据做分析，输出学习反馈，并给出“下一轮课标再分析触发条件与建议”。\n"
                    f"响应证据：\n{diagnosis_json}\n"
                )

        try:
            requested_max_tokens = int(requested_max_tokens) if requested_max_tokens is not None else None
        except Exception:
            requested_max_tokens = None

        effective_max_tokens = requested_max_tokens or Config.LESSON_MAX_COMPLETION_TOKENS
        if want_json and strict_example_structure:
            effective_max_tokens = max(effective_max_tokens, 12000)

        lesson_plan_raw = ai_service.generate_lesson_text(prompt, max_completion_tokens=effective_max_tokens)

        if want_json:
            extract_result = extract_json_three_stage(lesson_plan_raw, llm_cleaner=_clean_json_with_llm)
            parse_status = extract_result.get("stage", "failed")
            lesson_plan_json = extract_result.get("value")

            if not isinstance(lesson_plan_json, dict):
                need_review = True
                validation_status = "need_review"
                review_reasons.append("json_extract_failed")
                lesson_plan_json = _build_need_review_template(
                    lesson_title=lesson_title,
                    grade=grade,
                    subject=subject,
                    topic=topic,
                    reasons=review_reasons,
                    lang=lang,
                )
            else:
                valid_required, missing = _validate_required_json_fields(lesson_plan_json, required_fields)
                if not valid_required:
                    need_review = True
                    review_reasons.append(f"missing_fields:{','.join(missing)}")

                if thesis_mode:
                    thesis_errors = _validate_uk_thesis_payload(lesson_plan_json, year_group=year_group)
                    if thesis_errors:
                        need_review = True
                        validation_status = "need_review"
                        review_reasons.extend([f"thesis:{x}" for x in thesis_errors[:12]])
                    else:
                        validation_status = "passed"
                    lesson_plan_json = _ensure_legacy_lesson_fields(lesson_plan_json, fallback_title=lesson_title)
                    lesson_plan_json = _ensure_display_completeness(lesson_plan_json, key_points=key_points, lang=lang)
                else:
                    schema_ok, normalized_json, schema_errors = validate_lesson_payload(lesson_plan_json)
                    if not schema_ok:
                        need_review = True
                        validation_status = "need_review"
                        review_reasons.extend([f"schema:{x}" for x in schema_errors[:10]])
                        lesson_plan_json = _build_need_review_template(
                            lesson_title=lesson_title,
                            grade=grade,
                            subject=subject,
                            topic=topic,
                            reasons=review_reasons,
                            lang=lang,
                        )
                    else:
                        validation_status = "passed"
                        lesson_plan_json = _ensure_display_completeness(normalized_json, key_points=key_points, lang=lang)

                if math_rule_mode and isinstance(lesson_plan_json, dict):
                    allowed_prereq = retrieved_knowledge.get("allowed_prerequisites") if isinstance(retrieved_knowledge, dict) else None
                    math_ok, math_validation_errors = verify_math_content(
                        lesson_plan_json,
                        allowed_prerequisites=allowed_prereq,
                    )
                    if not math_ok:
                        need_review = True
                        math_status = "need_review"
                        review_reasons.extend([f"math:{x}" for x in math_validation_errors[:10]])
                    else:
                        math_status = "passed"

                meta_obj = lesson_plan_json.get("_meta") if isinstance(lesson_plan_json.get("_meta"), dict) else {}
                meta_obj.update(
                    {
                        "status": "need_review" if need_review else "ok",
                        "review_reasons": review_reasons,
                        "parse_stage": parse_status,
                        "teacher_review_required": bool(thesis_mode),
                        "teacher_review_approved": False,
                        "thesis_mode": bool(thesis_mode),
                        "locale": "en-GB" if thesis_mode else ("en" if lang == "en" else "zh-CN"),
                        "jurisdiction": "England" if thesis_mode else "",
                        "workflow_step": workflow_step,
                    }
                )
                if isinstance(class_diagnosis, dict):
                    meta_obj["learning_diagnosis_summary"] = class_diagnosis.get("summary")
                lesson_plan_json["_meta"] = meta_obj

                # Add optional formula and geometry support hints for math lessons.
                if (subject or "") in ["数学", "Math", "math"]:
                    lesson_plan_json["formula_hints"] = build_formula_hints(
                        topic=topic,
                        core_formula=lesson_plan_json.get("core_formula") if isinstance(lesson_plan_json, dict) else None,
                    )
                    lesson_plan_json["diagram_suggestions"] = build_diagram_suggestions(topic=topic)

            lesson_plan = json.dumps(lesson_plan_json, ensure_ascii=False, indent=2)
        else:
            lesson_plan = _sanitize_lesson_plan(lesson_plan_raw, grade, subject, topic, lang=lang)

        meta = {
            "topic": topic,
            "grade": grade,
            "subject": subject,
            "duration": duration,
            "lesson_count": lesson_count,
            "session_index": session_index,
            "session_total": session_total,
            "session_focus": session_focus,
            "source_topic": source_topic,
            "objectives": objectives,
            "key_points": key_points,
            "activities": activities,
            "output_format": "json" if want_json else "text",
            "strict_example_structure": bool(strict_example_structure),
            "math_rule_mode": bool(math_rule_mode),
            "use_knowledge_retrieval": bool(use_knowledge_retrieval),
            "use_symbolic_verification": bool(use_symbolic_verification),
            "workflow_id": workflow.id if workflow else None,
            "workflow_step": workflow_step,
            "class_id": class_id or None,
            "include_review_feedback": bool(include_review_feedback),
            "review_feedback_count": int(review_feedback_count),
            "need_review": bool(need_review),
            "review_reasons": review_reasons,
            "thesis_mode": bool(thesis_mode),
            "teacher_review_required": bool(thesis_mode),
            "teacher_review_approved": False,
        }
        if isinstance(class_diagnosis, dict):
            meta["learning_diagnosis_summary"] = class_diagnosis.get("summary")
        description = f"__META__{json.dumps(meta, ensure_ascii=False)}__\n" + lesson_plan

        lesson = Lesson(
            title=topic or "教案",
            description=description,
            created_by=created_by,
            created_at=datetime.datetime.now(),
            version=1,
            root_lesson_id=None,
            parent_lesson_id=None,
        )
        db.session.add(lesson)

        _update_workflow_after_generation(
            workflow,
            workflow_step,
            lesson_plan,
            "need_review" if need_review else "completed",
        )

        _create_generation_log(
            created_by=created_by,
            workflow_id=workflow.id if workflow else None,
            lesson_id=None,
            step_no=workflow_step,
            parse_status=parse_status,
            validation_status=validation_status,
            math_status=math_status,
            failure_reason=("; ".join(review_reasons) if review_reasons else None),
            raw_output=lesson_plan_raw,
            extracted_output=lesson_plan_json if want_json else lesson_plan,
            need_review=need_review,
        )

        db.session.flush()

        logs = GenerationLog.query.filter_by(
            created_by=created_by,
            workflow_id=(workflow.id if workflow else None),
            lesson_id=None,
            step_no=workflow_step,
        ).order_by(GenerationLog.id.desc()).limit(1).all()
        if logs:
            logs[0].lesson_id = lesson.id

        if not lesson.root_lesson_id:
            lesson.root_lesson_id = lesson.id

        _create_validation_log(
            created_by=created_by,
            entity_type="lesson",
            entity_id=lesson.id,
            workflow_id=(workflow.id if workflow else None),
            step_no=workflow_step,
            parse_status=parse_status,
            validation_status=validation_status,
            need_review=need_review,
            reasons=review_reasons,
        )

        db.session.commit()

        payload = {
            "lesson_plan": lesson_plan,
            "lesson_id": lesson.id,
            "workflow_id": workflow.id if workflow else None,
            "workflow_step": workflow_step,
            "need_review": bool(need_review),
            "review_reasons": review_reasons,
            "review_feedback_count": int(review_feedback_count),
        }
        if lesson_plan_json is not None:
            payload["lesson_plan_json"] = lesson_plan_json
        if math_rule_mode:
            payload["math_validation"] = {
                "enabled": True,
                "passed": len(math_validation_errors) == 0,
                "errors": math_validation_errors,
                "retrieval_applied": bool(retrieval_context_block),
            }
            if isinstance(tooling_bundle, dict):
                payload["tool_generated_assets"] = tooling_bundle
        return ok(payload)
    except Exception as e:
        print(f"Lesson generation error: {str(e)}")  # 调试日志
        return err(f"AI 生成失败: {str(e)}", http_status=500)



@bp.route('/history', methods=['GET'])
@token_required
def lesson_history():
    try:
        user_id = getattr(g, 'current_user_id', None)
        if not user_id:
            # 如果 token 无用户，返回最近公共记录
            lessons = Lesson.query.order_by(Lesson.created_at.desc()).limit(20).all()
        else:
            lessons = Lesson.query.filter_by(created_by=int(user_id)).order_by(Lesson.created_at.desc()).limit(20).all()

        result = []
        for l in lessons:
            d = l.to_dict()
            desc = d.get('content') or ''
            if desc.startswith('__META__'):
                try:
                    meta_str, real_content = desc.split('__\n', 1)
                    meta = json.loads(meta_str.replace('__META__',''))
                    d.update(meta)
                    d['content'] = real_content
                except Exception:
                    pass
            result.append(d)
        return ok(result)
    except Exception as e:
        return err(f"历史获取失败: {str(e)}", http_status=500)


@bp.route('/validation-logs', methods=['GET'])
@token_required
def validation_logs():
    try:
        user_id = int(getattr(g, 'current_user_id', 0) or 0)
        if not user_id:
            return err("missing user", http_status=401)

        entity_type = (request.args.get('entity_type') or '').strip().lower()
        limit = int(request.args.get('limit') or 100)
        limit = max(1, min(limit, 300))

        q = ValidationLog.query.filter_by(created_by=user_id)
        if entity_type in ('lesson', 'exercise'):
            q = q.filter_by(entity_type=entity_type)

        rows = q.order_by(ValidationLog.created_at.desc()).limit(limit).all()
        result = []
        for r in rows:
            reasons = []
            try:
                reasons = json.loads(r.reasons_json or '[]')
                if not isinstance(reasons, list):
                    reasons = []
            except Exception:
                reasons = []
            result.append(
                {
                    'id': r.id,
                    'entity_type': r.entity_type,
                    'entity_id': r.entity_id,
                    'workflow_id': r.workflow_id,
                    'step_no': r.step_no,
                    'parse_status': r.parse_status,
                    'validation_status': r.validation_status,
                    'need_review': bool(r.need_review),
                    'reasons': reasons,
                    'review_reason': r.review_reason or '',
                    'created_at': r.created_at.strftime('%Y-%m-%d %H:%M:%S') if r.created_at else '',
                }
            )
        return ok(result)
    except Exception as e:
        return err(f"validation logs failed: {str(e)}", http_status=500)


@bp.route('/<int:lesson_id>', methods=['DELETE'])
@token_required
def delete_lesson(lesson_id: int):
    try:
        user_id = getattr(g, 'current_user_id', None)
        if not user_id:
            return err("缺少用户ID", http_status=400)
        lesson = Lesson.query.get(lesson_id)
        if not lesson or lesson.created_by != int(user_id):
            return err("lesson not found", http_status=404)
        db.session.delete(lesson)
        db.session.commit()
        return ok({"deleted": True})
    except Exception as e:
        return err(f"删除失败: {str(e)}", http_status=500)


@bp.route('/<int:lesson_id>', methods=['PUT'])
@token_required
def update_lesson(lesson_id: int):
    try:
        user_id = getattr(g, 'current_user_id', None)
        if not user_id:
            return err("缺少用户ID", http_status=400)
        lesson = Lesson.query.get(lesson_id)
        if not lesson or lesson.created_by != int(user_id):
            return err("lesson not found", http_status=404)

        data = request.get_json(silent=True) or {}
        content = (data.get("content") or "").strip()
        title = data.get("title") or lesson.title
        incoming_meta = data.get("meta") or {}
        existing_meta = _extract_meta_from_description(lesson.description)
        meta = dict(existing_meta)
        if isinstance(incoming_meta, dict):
            meta.update(incoming_meta)

        if isinstance(meta, dict):
            if bool(meta.get("teacher_review_required")) or bool(existing_meta.get("teacher_review_required")):
                meta["teacher_review_required"] = True
                meta["teacher_review_approved"] = True
                meta["teacher_review_approved_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if meta:
            description = f"__META__{json.dumps(meta, ensure_ascii=False)}__\n" + content
        else:
            description = content

        before_content = lesson.description or ""
        before_version = int(lesson.version or 1)
        lesson.title = title
        lesson.description = description
        lesson.parent_lesson_id = lesson.parent_lesson_id or lesson.id
        lesson.root_lesson_id = lesson.root_lesson_id or lesson.id
        lesson.version = before_version + 1

        diff_obj = _compute_text_diff(before_content, description)
        edit_log = LessonEditLog(
            lesson_id=lesson.id,
            edited_by=int(user_id),
            version_from=before_version,
            version_to=lesson.version,
            before_content=before_content,
            after_content=description,
            diff_json=json.dumps(diff_obj, ensure_ascii=False),
            created_at=datetime.datetime.now(),
        )
        db.session.add(edit_log)
        db.session.commit()
        return ok({"updated": True, "version": lesson.version, "edit_log_id": edit_log.id})
    except Exception as e:
        return err(f"保存失败: {str(e)}", http_status=500)


@bp.route('/<int:lesson_id>/versions', methods=['GET'])
@token_required
def lesson_versions(lesson_id: int):
    try:
        user_id = getattr(g, 'current_user_id', None)
        if not user_id:
            return err("缺少用户ID", http_status=400)
        lesson = Lesson.query.get(lesson_id)
        if not lesson or lesson.created_by != int(user_id):
            return err("lesson not found", http_status=404)

        logs = LessonEditLog.query.filter_by(lesson_id=lesson.id).order_by(LessonEditLog.created_at.desc()).all()
        payload = []
        for x in logs:
            payload.append({
                "id": x.id,
                "version_from": x.version_from,
                "version_to": x.version_to,
                "edited_by": x.edited_by,
                "created_at": x.created_at.strftime('%Y-%m-%d %H:%M:%S') if x.created_at else "",
            })
        return ok({"lesson_id": lesson.id, "current_version": int(lesson.version or 1), "versions": payload})
    except Exception as e:
        return err(f"版本历史获取失败: {str(e)}", http_status=500)


@bp.route('/<int:lesson_id>/rollback', methods=['POST'])
@token_required
def rollback_lesson(lesson_id: int):
    try:
        user_id = getattr(g, 'current_user_id', None)
        if not user_id:
            return err("缺少用户ID", http_status=400)
        lesson = Lesson.query.get(lesson_id)
        if not lesson or lesson.created_by != int(user_id):
            return err("lesson not found", http_status=404)

        data = request.get_json(silent=True) or {}
        target_version = int(data.get("target_version") or 0)
        if target_version <= 0:
            return err("target_version is required", http_status=400)

        # target_version means content state after applying version_to == target_version.
        target_log = (
            LessonEditLog.query
            .filter(
                LessonEditLog.lesson_id == lesson.id,
                LessonEditLog.version_to == target_version,
            )
            .order_by(LessonEditLog.id.desc())
            .first()
        )
        if not target_log:
            return err("target version not found", http_status=404)

        before_content = lesson.description or ""
        before_version = int(lesson.version or 1)
        lesson.description = target_log.after_content or ""
        lesson.version = before_version + 1

        diff_obj = _compute_text_diff(before_content, lesson.description)
        rollback_log = LessonEditLog(
            lesson_id=lesson.id,
            edited_by=int(user_id),
            version_from=before_version,
            version_to=lesson.version,
            before_content=before_content,
            after_content=lesson.description,
            diff_json=json.dumps(diff_obj, ensure_ascii=False),
            created_at=datetime.datetime.now(),
        )
        db.session.add(rollback_log)
        db.session.commit()
        return ok({"rolled_back": True, "current_version": lesson.version, "rollback_log_id": rollback_log.id})
    except Exception as e:
        return err(f"回滚失败: {str(e)}", http_status=500)


@bp.route('/<int:lesson_id>/versions/<int:log_id>', methods=['GET'])
@token_required
def lesson_version_detail(lesson_id: int, log_id: int):
    try:
        user_id = getattr(g, 'current_user_id', None)
        if not user_id:
            return err("缺少用户ID", http_status=400)

        lesson = Lesson.query.get(lesson_id)
        if not lesson or lesson.created_by != int(user_id):
            return err("lesson not found", http_status=404)

        edit_log = LessonEditLog.query.filter_by(id=log_id, lesson_id=lesson.id).first()
        if not edit_log:
            return err("version log not found", http_status=404)

        diff_obj = safe_json_loads(edit_log.diff_json, {})
        if not isinstance(diff_obj, dict):
            diff_obj = {}

        payload = {
            "id": edit_log.id,
            "lesson_id": lesson.id,
            "version_from": int(edit_log.version_from or 0),
            "version_to": int(edit_log.version_to or 0),
            "created_at": edit_log.created_at.strftime('%Y-%m-%d %H:%M:%S') if edit_log.created_at else "",
            "diff": diff_obj,
            "before_content": edit_log.before_content or "",
            "after_content": edit_log.after_content or "",
        }
        return ok(payload)
    except Exception as e:
        return err(f"版本明细获取失败: {str(e)}", http_status=500)


@bp.route('/workflow/<int:workflow_id>', methods=['GET'])
@token_required
def workflow_detail(workflow_id: int):
    user_id = int(getattr(g, 'current_user_id', 0) or 0)
    if not user_id:
        return err("缺少用户ID", http_status=400)

    wf = LessonWorkflow.query.get(workflow_id)
    if not wf or int(wf.created_by) != user_id:
        return err("workflow not found", http_status=404)

    status_obj = _coerce_json_dict(wf.status_json, _default_workflow_status())
    content_obj = _coerce_json_dict(wf.content_json, {})
    return ok(
        {
            "workflow_id": wf.id,
            "topic": wf.topic,
            "subject": wf.subject,
            "grade": wf.grade,
            "current_step": int(wf.current_step or 1),
            "is_completed": bool(wf.is_completed),
            "status": status_obj,
            "content": content_obj,
            "created_at": wf.created_at.strftime('%Y-%m-%d %H:%M:%S') if wf.created_at else "",
            "updated_at": wf.updated_at.strftime('%Y-%m-%d %H:%M:%S') if wf.updated_at else "",
        }
    )


@bp.route('/workflow/<int:workflow_id>/iteration', methods=['GET'])
@token_required
def workflow_iteration_preview(workflow_id: int):
    user_id = int(getattr(g, 'current_user_id', 0) or 0)
    if not user_id:
        return err("缺少用户ID", http_status=400)

    wf = LessonWorkflow.query.get(workflow_id)
    if not wf or int(wf.created_by) != user_id:
        return err("workflow not found", http_status=404)

    status_obj = _coerce_json_dict(wf.status_json, _default_workflow_status())
    step6_status = status_obj.get("step_6")

    class_id = int(request.args.get("class_id") or 0)
    lang = (request.args.get("lang") or "zh").strip().lower()
    diagnosis = _build_student_learning_diagnosis(
        created_by=user_id,
        class_id=class_id,
        topic=wf.topic or "",
        lang=lang,
    )
    seed_text = _build_iteration_seed_from_workflow(wf, diagnosis, lang=lang)

    trigger_reanalysis = bool((diagnosis.get("completion_rate") or 0) < 85)
    if diagnosis.get("avg_score") is not None and diagnosis.get("avg_score") < 75:
        trigger_reanalysis = True
    if diagnosis.get("common_misconceptions"):
        trigger_reanalysis = True

    return ok(
        {
            "workflow_id": wf.id,
            "step6_status": step6_status,
            "trigger_curriculum_reanalysis": trigger_reanalysis,
            "diagnosis": diagnosis,
            "next_cycle_seed": seed_text,
        }
    )


@bp.route('/workflow/<int:workflow_id>/next-cycle', methods=['POST'])
@token_required
def workflow_start_next_cycle(workflow_id: int):
    user_id = int(getattr(g, 'current_user_id', 0) or 0)
    if not user_id:
        return err("缺少用户ID", http_status=400)

    wf = LessonWorkflow.query.get(workflow_id)
    if not wf or int(wf.created_by) != user_id:
        return err("workflow not found", http_status=404)

    status_obj = _coerce_json_dict(wf.status_json, _default_workflow_status())
    if status_obj.get("step_6") not in ("completed", "need_review"):
        return err("必须先完成第6步（课后评价）才能触发下一轮", http_status=409)

    data = request.get_json(silent=True) or {}
    class_id = int(data.get("class_id") or 0)
    lang = (data.get("lang") or "zh").strip().lower()

    diagnosis = _build_student_learning_diagnosis(
        created_by=user_id,
        class_id=class_id,
        topic=wf.topic or "",
        lang=lang,
    )
    seed_text = _build_iteration_seed_from_workflow(wf, diagnosis, lang=lang)

    new_status = _default_workflow_status()
    new_status["step_1"] = "completed"
    new_content = {
        "step_1": seed_text,
        "_loop_trace": {
            "from_workflow_id": wf.id,
            "trigger": "post_lesson_evaluation",
            "diagnosis_summary": diagnosis.get("summary"),
            "triggered_at": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        },
    }

    new_wf = LessonWorkflow(
        created_by=user_id,
        topic=wf.topic,
        subject=wf.subject,
        grade=wf.grade,
        current_step=2,
        is_completed=False,
        status_json=json.dumps(new_status, ensure_ascii=False),
        content_json=json.dumps(new_content, ensure_ascii=False),
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now(),
    )
    db.session.add(new_wf)
    db.session.commit()

    return ok(
        {
            "source_workflow_id": wf.id,
            "new_workflow_id": new_wf.id,
            "trigger_curriculum_reanalysis": True,
            "seed_step_1": seed_text,
            "diagnosis": diagnosis,
        }
    )