# app/api/lesson/routes.py
from flask import Blueprint, request, g
from app.utils.response import ok, err
from app.config import Config

from app.extensions import db
from app.models.lesson import Lesson
from app.utils.auth import token_required
from app.services.ai_service import ai_service
from app.utils.json_handlers import extract_json
import datetime, json
import os
import re

bp = Blueprint("lesson", __name__, url_prefix="/api/lesson")
_EXAMPLE_STRUCTURE_TEMPLATE = None


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
    is_en = (lang or "zh").lower() == "en"
    if is_en:
        return [
            "title",
            "teacher",
            "basic_information",
            "teaching_objectives",
            "key_and_difficult_points",
            "teaching_process",
            "assessment_and_feedback",
            "homework_design",
        ]
    return [
        "title",
        "teacher",
        "basic_information",
        "teaching_objectives",
        "key_points_and_difficulties",
        "teaching_process",
        "assessment_and_feedback",
        "homework_design",
    ]


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


def _contains_cjk_text(text: str) -> bool:
    if not text:
        return False
    return bool(re.search(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]", text))


def _json_contains_cjk_values(value) -> bool:
    if isinstance(value, str):
        return _contains_cjk_text(value)
    if isinstance(value, list):
        return any(_json_contains_cjk_values(v) for v in value)
    if isinstance(value, dict):
        return any(_json_contains_cjk_values(v) for v in value.values())
    return False


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

    if not topic:
        return err("topic is required", http_status=400)

    lesson_title = _build_lesson_title(grade, subject, topic, lang=lang)

    prompt_zh = f"""
你是一名小学数学教案编写专家。请严格按下面格式输出，不要解释，不要前言，不要“根据您提供的信息”之类句子，不要 Markdown 代码块。

输入信息：
- 年级：{grade}
- 学科：{subject}
- 课题：{topic}
- 课时：{duration} 分钟
- 节数：{lesson_count}
- 教学目标：{objectives}
- 重难点：{key_points}
- 教学活动：{activities}

输出规范（必须遵守）：
1) 第一行必须是：{lesson_title}
2) 第二行必须是：执教者：[您的姓名]
3) 标题层级必须统一：
   - 一级标题：中文大写序号，如“一、 基本信息”
   - 二级标题：阿拉伯数字序号，如“1. 知识与技能”
   - 三级标题：无序号短标题，如“教学重点：”
4) 至少包含以下一级标题：
   - 一、 基本信息
   - 二、 教学目标
   - 三、 重难点
   - 四、 教学过程
   - 五、 评价与反馈
   - 六、 作业设计
5) 内容必须可直接用于打印，不得出现“示例/模板/可选/待补充”等提示词。

如果节数大于1，请按“第1课时、第2课时...”分节，每节内保持同样的层级规范。
"""

    prompt_en = f"""
You are an expert K-12 lesson plan writer. Output only the lesson content in English.
Do not add any preface, explanation, markdown code block, or phrases like "Based on the information you provided".
All user-facing text must be English only. Do not output any Chinese characters.

Input:
- Grade: {grade}
- Subject: {subject}
- Topic: {topic}
- Duration: {duration} minutes
- Lesson count: {lesson_count}
- Teaching objectives: {objectives}
- Key points: {key_points}
- Activities: {activities}

Required format:
1) First line must be exactly: {lesson_title}
2) Second line must be exactly: Teacher: [Your Name]
3) Heading levels:
   - Level 1: Roman numerals, e.g. "I. Basic Information"
   - Level 2: Arabic numerals, e.g. "1. Knowledge and Skills"
   - Level 3: Short label lines, e.g. "Teaching Focus:"
4) Must include these Level-1 sections:
   - I. Basic Information
   - II. Teaching Objectives
   - III. Key and Difficult Points
   - IV. Teaching Process
   - V. Assessment and Feedback
   - VI. Homework Design
5) The output should be classroom-ready. Do not use words like "template", "optional", or "to be filled".

If lesson_count > 1, split into "Lesson 1, Lesson 2..." while keeping the same heading hierarchy.
"""

    prompt = prompt_en if lang == "en" else prompt_zh

    if want_json:
        required_fields = required_json_fields or _default_lesson_json_required_fields(lang=lang)
        schema_text = json.dumps(json_schema, ensure_ascii=False, indent=2) if json_schema else ""
        example_template = None
        example_skeleton = None
        if strict_example_structure:
            example_template = _load_example_structure_template()
            example_skeleton = _skeleton_from_template(example_template)

        prompt_json_zh = f"""
你是一名小学数学教案编写专家。
请只输出一个 JSON 对象，不要输出任何解释、前后缀文本或 Markdown 代码块。

输入信息：
- 年级：{grade}
- 学科：{subject}
- 课题：{topic}
- 课时：{duration} 分钟
- 节数：{lesson_count}
- 教学目标：{objectives}
- 重难点：{key_points}
- 教学活动：{activities}

硬性要求：
1) 顶层必须是 JSON 对象。
2) 不允许返回多余说明文字。
"""
        prompt_json_en = f"""
You are an expert K-12 lesson plan writer.
Return one JSON object only. Do not output explanations, prefixes, or markdown code blocks.
    All string values must be English only. Do not include Chinese characters in any value.

Input:
- Grade: {grade}
- Subject: {subject}
- Topic: {topic}
- Duration: {duration} minutes
- Lesson count: {lesson_count}
- Teaching objectives: {objectives}
- Key points: {key_points}
- Activities: {activities}

Hard requirements:
1) Top-level value must be a JSON object.
2) No extra text outside JSON.
"""
        if strict_example_structure and example_skeleton is not None:
            prompt_json_zh += (
                "\n你必须严格按照下方结构模板输出："
                "键名必须完全一致，层级必须完全一致，不允许新增键、不允许缺失键；"
                "数组项的数据结构必须与模板一致，值内容可根据本次输入改写。\n"
                f"结构模板：\n{json.dumps(example_skeleton, ensure_ascii=False, indent=2)}\n"
            )
            prompt_json_en += (
                "\nYou must strictly follow this structure template: "
                "key names and nesting must match exactly, with no extra or missing keys; "
                "array item structures must also match. Values can be rewritten for this lesson context.\n"
                f"Structure template:\n{json.dumps(example_skeleton, ensure_ascii=False, indent=2)}\n"
            )
        elif required_json_fields is None:
            prompt_json_zh += f"\n必须包含字段：{json.dumps(required_fields, ensure_ascii=False)}\n"
            prompt_json_en += f"\nRequired fields: {json.dumps(required_fields, ensure_ascii=False)}\n"

        if schema_text:
            prompt_json_zh += f"\n请严格遵循以下 JSON Schema：\n{schema_text}\n"
            prompt_json_en += f"\nYou must strictly follow this JSON schema:\n{schema_text}\n"
        prompt = prompt_json_en if lang == "en" else prompt_json_zh

    try:
        if not Config.OPENAI_API_KEY:
            return err("OpenAI API key not configured", http_status=500)

        try:
            requested_max_tokens = int(requested_max_tokens) if requested_max_tokens is not None else None
        except Exception:
            requested_max_tokens = None

        effective_max_tokens = requested_max_tokens or Config.LESSON_MAX_COMPLETION_TOKENS
        if want_json and strict_example_structure:
            effective_max_tokens = max(effective_max_tokens, 12000)
        
        try:
            lesson_plan_raw = ai_service.generate_lesson_text(prompt, max_completion_tokens=effective_max_tokens)
        except RuntimeError as gen_err:
            if "finish_reason=length" not in str(gen_err):
                raise

            # Length-truncated response fallback: enforce concise values and retry with a larger token budget.
            compact_hint_zh = (
                "\n\n额外要求（防截断）：\n"
                "- 每个字符串字段尽量简洁，通常 1-2 句。\n"
                "- 数组字段尽量 1-3 项即可。\n"
                "- 在满足结构的前提下避免冗长叙述。"
            )
            compact_hint_en = (
                "\n\nExtra anti-truncation requirements:\n"
                "- Keep each string value concise (usually 1-2 sentences).\n"
                "- Keep arrays short (usually 1-3 items).\n"
                "- Avoid long narrative while preserving required structure."
            )
            retry_prompt = prompt + (compact_hint_en if lang == "en" else compact_hint_zh)
            retry_max_tokens = max(effective_max_tokens, 16000)
            lesson_plan_raw = ai_service.generate_lesson_text(retry_prompt, max_completion_tokens=retry_max_tokens)

        lesson_plan_json = None
        if want_json:
            example_template = _load_example_structure_template() if strict_example_structure else None
            lesson_plan_json = extract_json(lesson_plan_raw)
            if not isinstance(lesson_plan_json, dict):
                return err("AI 未按 JSON 格式输出，请重试或收紧 schema", http_status=500)

            if example_template is not None:
                structure_errors = _validate_json_structure_with_template(lesson_plan_json, example_template)
                if structure_errors:
                    repair_prompt = (
                        "Return one corrected JSON object only. "
                        "Fix all structure errors listed below and keep the same lesson intent.\n\n"
                        f"Structure errors:\n- " + "\n- ".join(structure_errors[:30]) + "\n\n"
                        "Expected structure template (keys and nesting):\n"
                        f"{json.dumps(_skeleton_from_template(example_template), ensure_ascii=False, indent=2)}\n\n"
                        "Your previous JSON:\n"
                        f"{json.dumps(lesson_plan_json, ensure_ascii=False, indent=2)}"
                    )
                    repaired_raw = ai_service.generate_lesson_text(repair_prompt)
                    repaired_json = extract_json(repaired_raw)
                    if not isinstance(repaired_json, dict):
                        return err("AI 未按 example.json 结构输出（重试后仍失败）", http_status=500)
                    repaired_errors = _validate_json_structure_with_template(repaired_json, example_template)
                    if repaired_errors:
                        brief = "; ".join(repaired_errors[:8])
                        return err(f"AI 未按 example.json 结构输出: {brief}", http_status=500)
                    lesson_plan_json = repaired_json
            else:
                required_fields = required_json_fields or _default_lesson_json_required_fields(lang=lang)
                valid, missing = _validate_required_json_fields(lesson_plan_json, required_fields)
                if not valid:
                    return err(f"AI JSON 缺少必填字段: {', '.join(missing)}", http_status=500)

            resource_errors = _validate_semantic_resource_fields(lesson_plan_json)
            if resource_errors:
                resource_fix_prompt = (
                    "Return one corrected JSON object only. Keep the same structure and fill resource fields meaningfully.\n\n"
                    "Fix these semantic errors:\n- " + "\n- ".join(resource_errors[:20]) + "\n\n"
                    "Constraints:\n"
                    "- resources_summary must contain concrete classroom resources.\n"
                    "- external_resources must include at least one usable reference with title/description/suggested_use.\n"
                    "- Keep all keys and nesting unchanged.\n\n"
                    "Current JSON:\n"
                    f"{json.dumps(lesson_plan_json, ensure_ascii=False, indent=2)}"
                )
                resource_fixed_raw = ai_service.generate_lesson_text(
                    resource_fix_prompt,
                    max_completion_tokens=max(effective_max_tokens, 12000),
                )
                resource_fixed_json = extract_json(resource_fixed_raw)
                if not isinstance(resource_fixed_json, dict):
                    return err("AI 资源字段补全失败（返回非 JSON）", http_status=500)
                resource_recheck = _validate_semantic_resource_fields(resource_fixed_json)
                if resource_recheck:
                    brief = "; ".join(resource_recheck[:6])
                    return err(f"AI 资源字段补全失败: {brief}", http_status=500)
                lesson_plan_json = resource_fixed_json

            if lang == "en" and _json_contains_cjk_values(lesson_plan_json):
                english_repair_prompt = (
                    "Return one corrected JSON object only. "
                    "Translate all Chinese text values to natural English while preserving the exact same JSON keys, nesting, and array structures. "
                    "Do not add or remove keys. Do not output extra text.\n\n"
                    "Current JSON:\n"
                    f"{json.dumps(lesson_plan_json, ensure_ascii=False, indent=2)}"
                )
                english_fixed_raw = ai_service.generate_lesson_text(
                    english_repair_prompt,
                    max_completion_tokens=max(effective_max_tokens, 12000),
                )
                english_fixed_json = extract_json(english_fixed_raw)
                if not isinstance(english_fixed_json, dict):
                    return err("AI 英文输出修复失败（返回非 JSON）", http_status=500)

                if example_template is not None:
                    english_structure_errors = _validate_json_structure_with_template(english_fixed_json, example_template)
                    if english_structure_errors:
                        brief = "; ".join(english_structure_errors[:6])
                        return err(f"AI 英文输出修复失败（结构异常）: {brief}", http_status=500)
                else:
                    required_fields = required_json_fields or _default_lesson_json_required_fields(lang=lang)
                    valid, missing = _validate_required_json_fields(english_fixed_json, required_fields)
                    if not valid:
                        return err(f"AI 英文输出修复失败（字段缺失）: {', '.join(missing)}", http_status=500)

                if _json_contains_cjk_values(english_fixed_json):
                    return err("AI 英文输出修复失败（仍包含中文）", http_status=500)
                lesson_plan_json = english_fixed_json

            lesson_plan = json.dumps(lesson_plan_json, ensure_ascii=False, indent=2)
        else:
            lesson_plan = _sanitize_lesson_plan(lesson_plan_raw, grade, subject, topic, lang=lang)
            if lang == "en" and _contains_cjk_text(lesson_plan):
                english_text_prompt = (
                    "Rewrite the following lesson plan into fully natural English only. "
                    "Preserve structure and headings. Return plain text only with no extra explanation.\n\n"
                    f"{lesson_plan}"
                )
                lesson_plan_rewritten = ai_service.generate_lesson_text(
                    english_text_prompt,
                    max_completion_tokens=max(effective_max_tokens, 12000),
                )
                lesson_plan = _sanitize_lesson_plan(lesson_plan_rewritten, grade, subject, topic, lang=lang)

        # 存档到数据库，序列化前端参数到 description 前缀
        meta = {
            'topic': topic,
            'grade': grade,
            'subject': subject,
            'duration': duration,
            'lesson_count': lesson_count,
            'objectives': objectives,
            'key_points': key_points,
            'activities': activities,
            'output_format': 'json' if want_json else 'text',
            'strict_example_structure': bool(strict_example_structure)
        }
        description = f"__META__{json.dumps(meta, ensure_ascii=False)}__\n" + lesson_plan

        # 从 token 中读取用户 id
        created_by = int(getattr(g, 'current_user_id', 0) or 0)

        lesson = Lesson(
            title=topic or '教案',
            description=description,
            created_by=created_by,
            created_at=datetime.datetime.now()
        )
        db.session.add(lesson)
        db.session.commit()

        payload = {"lesson_plan": lesson_plan, "lesson_id": lesson.id}
        if lesson_plan_json is not None:
            payload["lesson_plan_json"] = lesson_plan_json
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
            return err("missing user id", http_status=401)

        # 仅返回当前登录用户的教案历史，避免混入他人数据
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
        meta = data.get("meta") or {}

        if meta:
            description = f"__META__{json.dumps(meta, ensure_ascii=False)}__\n" + content
        else:
            description = content

        lesson.title = title
        lesson.description = description
        db.session.commit()
        return ok({"updated": True})
    except Exception as e:
        return err(f"保存失败: {str(e)}", http_status=500)