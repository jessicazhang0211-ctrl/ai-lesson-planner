# app/api/exercise/routes.py
from flask import Blueprint, request, g
from app.utils.response import ok, err
from app.models import Exercise
from app.models.validation_log import ValidationLog
from app.extensions import db
from app.utils.auth import token_required
from app.services.ai_service import ai_service
from app.services.exercise_adaptive_service import suggest_difficulty_ratio, generate_isomorphic_variants
from app.services.knowledge_base_service import build_knowledge_injection_context
from app.utils.json_handlers import extract_json
import json
import re
import importlib
import datetime
from io import BytesIO

try:
    from docx import Document
except Exception:
    Document = None

bp = Blueprint("exercise", __name__, url_prefix="/api/exercise")

_LESSON_FILE_MAX_CHARS = 12000


def _load_sympy():
    try:
        return importlib.import_module("sympy")
    except Exception:
        return None


def _normalize_math_expr(text: str) -> str:
    expr = (text or "").strip().replace("×", "*").replace("÷", "/").replace("^", "**")
    expr = expr.replace("，", ",").replace("。", "").replace("：", ":")
    return re.sub(r"\s+", "", expr)


def _extract_equation_candidate(text: str) -> str:
    raw = str(text or "")
    if "=" not in raw:
        return ""

    # Try to capture a compact equation segment from mixed natural-language stem.
    m = re.search(r"([0-9xX+\-*/().^×÷\s]+=[0-9xX+\-*/().^×÷\s]+)", raw)
    if m:
        return m.group(1)

    # Fallback: trim around first '=' and keep only math characters.
    left, right = raw.split("=", 1)
    left_keep = re.sub(r"[^0-9xX+\-*/().^×÷\s]", "", left)
    right_keep = re.sub(r"[^0-9xX+\-*/().^×÷\s]", "", right)
    candidate = f"{left_keep}={right_keep}"
    return candidate


def _parse_numeric_answer(answer):
    if isinstance(answer, (int, float)):
        return float(answer)
    if isinstance(answer, str):
        nums = re.findall(r"-?\d+(?:\.\d+)?", answer)
        if nums:
            return float(nums[-1])
    return None


def _verify_question_answer_consistency(question: str, answer) -> tuple[bool, bool, str]:
    text = str(question or "").strip()
    if not text:
        return False, True, ""

    sympy = _load_sympy()
    if sympy is None:
        return False, True, ""

    # Case A: arithmetic expression such as "12+3*4".
    if re.fullmatch(r"[\d\s+\-*/().^×÷=]+", text):
        expr_text = _normalize_math_expr(text.split("=", 1)[0])
        ans_num = _parse_numeric_answer(answer)
        if ans_num is None:
            return True, False, "answer_not_numeric"
        try:
            value = float(sympy.N(sympy.sympify(expr_text)))
            ok = abs(value - ans_num) <= 1e-6
            return True, ok, f"expected={value},answer={ans_num}" if not ok else ""
        except Exception:
            return False, True, ""

    # Case B: simple equation with x, e.g. "2*x+3=11" or mixed-language stem.
    eq_candidate = _extract_equation_candidate(text)
    if "=" in eq_candidate and ("x" in eq_candidate.lower()):
        normalized = _normalize_math_expr(eq_candidate)
        left_raw, right_raw = [x.strip() for x in normalized.split("=", 1)]
        ans_num = _parse_numeric_answer(answer)
        if ans_num is None:
            return True, False, "answer_not_numeric"
        try:
            x = sympy.symbols("x")
            sols = sympy.solve(sympy.sympify(left_raw) - sympy.sympify(right_raw), x)
            ok = any(abs(float(sympy.N(s)) - ans_num) <= 1e-6 for s in sols)
            return True, ok, f"solutions={sols},answer={ans_num}" if not ok else ""
        except Exception:
            return False, True, ""

    return False, True, ""


def _create_validation_log(created_by: int, exercise_id: int, parse_status: str, validation_status: str, need_review: bool, reasons: list):
    try:
        row = ValidationLog(
            created_by=int(created_by),
            entity_type="exercise",
            entity_id=exercise_id,
            workflow_id=None,
            step_no=5,
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


def _normalize_question_tiers(questions: list) -> list:
    rows = [q for q in (questions or []) if isinstance(q, dict)]
    if not rows:
        return rows

    n = len(rows)
    b_end = max(1, int(round(n * 0.4)))
    i_end = max(b_end + 1, int(round(n * 0.8)))

    for i, q in enumerate(rows):
        if not isinstance(q.get("difficulty_level"), str) or not q.get("difficulty_level", "").strip():
            if i < b_end:
                q["difficulty_level"] = "basic"
            elif i < i_end:
                q["difficulty_level"] = "improve"
            else:
                q["difficulty_level"] = "extend"

        if not isinstance(q.get("chain_role"), str) or not q.get("chain_role", "").strip():
            if i == 0:
                q["chain_role"] = "mother"
            elif i < max(2, int(round(n * 0.7))):
                q["chain_role"] = "isomorphic_variant"
            else:
                q["chain_role"] = "extension"
    return rows


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


def _safe_json_loads(raw: str, default):
    try:
        return json.loads(raw)
    except Exception:
        return default


def _normalize_generate_data(raw_data: dict) -> dict:
    data = dict(raw_data or {})
    types = data.get("types")
    if isinstance(types, str):
        parsed = _safe_json_loads(types, None)
        if isinstance(parsed, list):
            data["types"] = parsed
        else:
            data["types"] = [x.strip() for x in types.split(",") if x.strip()]
    elif not isinstance(types, list):
        data["types"] = []

    try:
        data["count"] = int(data.get("count") or 10)
    except Exception:
        data["count"] = 10

    try:
        data["class_accuracy"] = float(data.get("class_accuracy") or 0.0)
    except Exception:
        data["class_accuracy"] = 0.0

    return data


def _read_uploaded_lesson_text(file_storage) -> str:
    if not file_storage or not getattr(file_storage, "filename", ""):
        return ""

    filename = (file_storage.filename or "").lower()
    raw_bytes = file_storage.read() or b""
    if not raw_bytes:
        return ""

    if filename.endswith(".docx") and Document is not None:
        try:
            doc = Document(BytesIO(raw_bytes))
            text = "\n".join((p.text or "").strip() for p in doc.paragraphs if (p.text or "").strip())
            return text[:_LESSON_FILE_MAX_CHARS]
        except Exception:
            return ""

    for enc in ("utf-8", "utf-8-sig", "gbk"):
        try:
            return raw_bytes.decode(enc, errors="ignore")[:_LESSON_FILE_MAX_CHARS]
        except Exception:
            continue
    return ""


def _extract_focus_from_text(text: str) -> dict:
    cleaned = (text or "").replace("\r", "\n")
    if not cleaned.strip():
        return {}

    key_points = []
    difficult_points = []

    inline_key = re.findall(r"(?:教学重点|重点)\s*[:：]\s*(.+)", cleaned)
    inline_diff = re.findall(r"(?:教学难点|难点)\s*[:：]\s*(.+)", cleaned)
    key_points.extend([x.strip(" -；;。") for x in inline_key if x.strip()])
    difficult_points.extend([x.strip(" -；;。") for x in inline_diff if x.strip()])

    section_match = re.search(
        r"(?:教学)?重难点\s*[：:]?\s*\n([\s\S]{0,1200}?)(?:\n\s*(?:[一二三四五六七八九十\d]+[、.）)]|教学目标|教学过程|作业|评价|板书|课堂小结)|$)",
        cleaned,
        flags=re.IGNORECASE,
    )
    if section_match:
        block = section_match.group(1)
        for line in block.split("\n"):
            s = line.strip(" \t-•*1234567890.、）)")
            if not s:
                continue
            if any(k in s for k in ["难点", "困难"]):
                s = re.sub(r"^(?:教学难点|难点)\s*[:：]?", "", s).strip()
                if s:
                    difficult_points.append(s)
            else:
                s = re.sub(r"^(?:教学重点|重点)\s*[:：]?", "", s).strip()
                if s:
                    key_points.append(s)

    def _dedupe(items):
        seen = set()
        out = []
        for item in items:
            norm = re.sub(r"\s+", "", item)
            if not norm or norm in seen:
                continue
            seen.add(norm)
            out.append(item)
        return out[:6]

    key_points = _dedupe(key_points)
    difficult_points = _dedupe(difficult_points)
    result = {}
    if key_points:
        result["key_points"] = key_points
    if difficult_points:
        result["difficult_points"] = difficult_points
    return result


def _build_focus_prompt_block(lang: str, focus: dict) -> str:
    key_points = focus.get("key_points") or []
    difficult_points = focus.get("difficult_points") or []
    if not key_points and not difficult_points:
        return ""

    if lang == "en":
        key_line = "; ".join(key_points) if key_points else "N/A"
        diff_line = "; ".join(difficult_points) if difficult_points else "N/A"
        return (
            "\nLesson-plan focus reference (must be reflected in the generated questions):\n"
            f"- Key points: {key_line}\n"
            f"- Difficult points: {diff_line}\n"
        )

    key_line = "；".join(key_points) if key_points else "无"
    diff_line = "；".join(difficult_points) if difficult_points else "无"
    return (
        "\n教案重难点参考（生成习题时必须体现以下内容）：\n"
        f"- 重点：{key_line}\n"
        f"- 难点：{diff_line}\n"
    )


@bp.route("/generate", methods=["POST", "OPTIONS"])
@token_required
def generate_exercise():
    if request.method == "OPTIONS":
        return ok({"msg": "CORS preflight ok"})
    try:
        is_multipart = request.content_type and "multipart/form-data" in request.content_type.lower()
        data = request.form.to_dict(flat=True) if is_multipart else (request.get_json(silent=True) or {})
        data = _normalize_generate_data(data)
        lang = (data.get("lang") or "zh").strip().lower()
        user_id = getattr(g, 'current_user_id', None)
        if not user_id:
            return err("missing user id", http_status=400)

        lesson_file = request.files.get("lesson_file") if is_multipart else None
        lesson_text = (data.get("lesson_text") or "").strip()
        if lesson_file and getattr(lesson_file, "filename", ""):
            file_text = _read_uploaded_lesson_text(lesson_file)
            if file_text:
                lesson_text = file_text
                data["lesson_filename"] = lesson_file.filename

        lesson_focus = data.get("lesson_focus")
        if isinstance(lesson_focus, str):
            parsed_focus = _safe_json_loads(lesson_focus, {})
            lesson_focus = parsed_focus if isinstance(parsed_focus, dict) else {}
        elif not isinstance(lesson_focus, dict):
            lesson_focus = {}
        if not lesson_focus and lesson_text:
            lesson_focus = _extract_focus_from_text(lesson_text)

        class_accuracy = float(data.get("class_accuracy") or 0.0)
        try:
            class_id = int(data.get("class_id") or 0)
        except Exception:
            class_id = 0
        use_custom_knowledge_base = bool(data.get("use_custom_knowledge_base", True))
        difficulty_ratio = suggest_difficulty_ratio(class_accuracy)
        focus_block = _build_focus_prompt_block(lang, lesson_focus)

        prompt_zh = f"""
请根据以下信息生成{data.get('count', 10)}道{data.get('difficulty', '中等')}难度的{data.get('subject', '数学')}习题，题型包括{','.join(data.get('types', []))}，知识点/主题为：{data.get('topic', '')}。
{focus_block}

    难度比例建议（按班级历史正确率动态调整）：
    - easy: {difficulty_ratio.get('easy')}
    - medium: {difficulty_ratio.get('medium')}
    - hard: {difficulty_ratio.get('hard')}

请输出 JSON，结构如下：
{{
    "title": "...",
    "subject": "...",
    "grade": "...",
    "topic": "...",
    "questions": [
        {{
            "id": "q1",
            "type": "single|multi|true_false|fill|short",
            "difficulty_level": "basic|improve|extend",
            "chain_role": "mother|isomorphic_variant|extension",
            "stem": "题干",
            "options": ["A...","B..."],
            "answer": "A" 或 ["A","C"] 或 "true" 或 ["填空1","填空2"],
            "analysis": "解析",
            "score": 5
        }}
    ]
}}

仅输出 JSON，不要包含代码块或额外解释。
"""

        prompt_en = f"""
Generate {data.get('count', 10)} {data.get('difficulty', 'medium')} {data.get('subject', 'math')} questions.
Question types: {','.join(data.get('types', []))}. Topic: {data.get('topic', '')}.
    {focus_block}
    All user-facing text must be English only. Do not output any Chinese characters.

    Adaptive difficulty ratio guidance:
    - easy: {difficulty_ratio.get('easy')}
    - medium: {difficulty_ratio.get('medium')}
    - hard: {difficulty_ratio.get('hard')}

Return JSON in this format:
{{
    "title": "...",
    "subject": "...",
    "grade": "...",
    "topic": "...",
    "questions": [
        {{
            "id": "q1",
            "type": "single|multi|true_false|fill|short",
            "difficulty_level": "basic|improve|extend",
            "chain_role": "mother|isomorphic_variant|extension",
            "stem": "question stem",
            "options": ["A...","B..."],
            "answer": "A" or ["A","C"] or "true" or ["blank1","blank2"],
            "analysis": "explanation",
            "score": 5
        }}
    ]
}}

Output JSON only. Do not include markdown code fences or extra text.
"""
        prompt = prompt_en if lang == "en" else prompt_zh

        if use_custom_knowledge_base:
            custom_kb_context = build_knowledge_injection_context(
                created_by=user_id,
                topic=data.get("topic", ""),
                class_id=class_id or None,
                lang=lang,
                limit=8,
            )
            if custom_kb_context:
                if lang == "en":
                    prompt += (
                        "\n\n[Custom user knowledge base]\n"
                        "Use the following imported knowledge as context for exercise design.\n"
                        f"{custom_kb_context}\n"
                    )
                else:
                    prompt += (
                        "\n\n【用户知识库注入】\n"
                        "请将以下用户导入的知识库内容作为习题设计上下文。\n"
                        f"{custom_kb_context}\n"
                    )

        content = ai_service.generate_text(prompt)
        structured = extract_json(content)

        if lang == "en":
            if isinstance(structured, dict) and _json_contains_cjk_values(structured):
                repair_prompt = (
                    "Return one corrected JSON object only. "
                    "Translate all Chinese text values to natural English while preserving the same keys, nesting, and array structures. "
                    "Do not add extra text.\n\n"
                    f"Current JSON:\n{json.dumps(structured, ensure_ascii=False, indent=2)}"
                )
                repaired_raw = ai_service.generate_text(repair_prompt)
                repaired_json = extract_json(repaired_raw)
                if isinstance(repaired_json, dict) and not _json_contains_cjk_values(repaired_json):
                    structured = repaired_json
                    content = json.dumps(repaired_json, ensure_ascii=False)
            elif structured is None and _contains_cjk_text(content):
                rewrite_prompt = (
                    "Rewrite the following exercise output into natural English only. "
                    "Preserve the original meaning and structure.\n\n"
                    f"{content}"
                )
                rewritten = ai_service.generate_text(rewrite_prompt)
                content = rewritten
                parsed = extract_json(rewritten)
                if isinstance(parsed, dict):
                    structured = parsed

        if isinstance(structured, dict):
            structured["questions"] = _normalize_question_tiers(
                structured.get("questions") if isinstance(structured.get("questions"), list) else []
            )

        parse_status = "parsed" if isinstance(structured, dict) else "extract_failed"
        validation_errors = []
        if isinstance(structured, dict):
            questions = structured.get("questions") if isinstance(structured.get("questions"), list) else []
            for idx, q in enumerate(questions):
                if not isinstance(q, dict):
                    continue
                checked, ok_result, msg = _verify_question_answer_consistency(q.get("stem") or "", q.get("answer"))
                if checked and not ok_result:
                    validation_errors.append(f"q{idx + 1}:{msg}")

        need_review = (structured is None) or bool(validation_errors)
        validation_status = "need_review" if need_review else "passed"

        # 存档到数据库，前端参数信息一并序列化进description前缀
        meta = {
            'topic': data.get('topic', ''),
            'grade': data.get('grade', ''),
            'subject': data.get('subject', ''),
            'types': data.get('types', []),
            'difficulty': data.get('difficulty', ''),
            'count': data.get('count', ''),
            'includeAnswer': data.get('includeAnswer', ''),
            'difficulty_ratio': difficulty_ratio,
            'lesson_focus': lesson_focus,
            'lesson_filename': data.get('lesson_filename', ''),
            'parse_status': parse_status,
            'validation_status': validation_status,
            'need_review': bool(need_review),
            'validation_errors': validation_errors[:20],
        }
        description = f"__META__{json.dumps(meta, ensure_ascii=False)}__\n" + content
        raw_json = None
        if structured is None:
            cleaned = content.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.replace("```json", "").replace("```", "").strip()
            if cleaned.startswith("{") and cleaned.endswith("}"):
                raw_json = cleaned
        exercise = Exercise(
            title=data.get('topic', '') or '习题',
            description=description,
            content_json=json.dumps(structured, ensure_ascii=False) if structured else raw_json,
            created_by=int(user_id),
            created_at=datetime.datetime.now()
        )
        db.session.add(exercise)
        db.session.flush()

        _create_validation_log(
            created_by=int(user_id),
            exercise_id=exercise.id,
            parse_status=parse_status,
            validation_status=validation_status,
            need_review=need_review,
            reasons=(validation_errors if validation_errors else (["json_extract_failed"] if structured is None else [])),
        )

        db.session.commit()
        return ok(
            {
                "content": content,
                "exercise_id": exercise.id,
                "difficulty_ratio": difficulty_ratio,
                "need_review": bool(need_review),
                "parse_status": parse_status,
                "validation_status": validation_status,
                "validation_errors": validation_errors[:20],
            }
        )
    except Exception as e:
        return err(f"AI generation failed: {str(e)}", http_status=500)


@bp.route("/adaptive-plan", methods=["POST"])
@token_required
def adaptive_plan():
    try:
        data = request.get_json(silent=True) or {}
        class_accuracy = float(data.get("class_accuracy") or 0.0)
        ratio = suggest_difficulty_ratio(class_accuracy)
        return ok({"class_accuracy": class_accuracy, "difficulty_ratio": ratio})
    except Exception as e:
        return err(f"adaptive plan failed: {str(e)}", http_status=500)


@bp.route("/variants", methods=["POST"])
@token_required
def exercise_variants():
    try:
        data = request.get_json(silent=True) or {}
        mother = data.get("mother_question") if isinstance(data.get("mother_question"), dict) else {}
        count = int(data.get("count") or 3)
        if not mother:
            return err("mother_question is required", http_status=400)
        variants = generate_isomorphic_variants(mother, count=count)
        return ok({"variants": variants})
    except Exception as e:
        return err(f"variant generation failed: {str(e)}", http_status=500)


@bp.route("/history", methods=["GET"])
@token_required
def exercise_history():
    try:
        user_id = getattr(g, 'current_user_id', None)
        if not user_id:
            return err("missing user id", http_status=400)
        # 查询最近生成的习题（按时间倒序，最多20条）
        exercises = Exercise.query.filter_by(created_by=int(user_id)).order_by(Exercise.created_at.desc()).limit(20).all()
        # 解析description前缀的meta
        result = []
        import json
        for e in exercises:
            d = e.to_dict()
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
        return err(f"history fetch failed: {str(e)}", http_status=500)


@bp.route('/<int:exercise_id>', methods=['DELETE'])
@token_required
def delete_exercise(exercise_id: int):
    try:
        user_id = getattr(g, 'current_user_id', None)
        if not user_id:
            return err("missing user id", http_status=400)
        exercise = Exercise.query.get(exercise_id)
        if not exercise or exercise.created_by != int(user_id):
            return err("exercise not found", http_status=404)
        from app.extensions import db
        db.session.delete(exercise)
        db.session.commit()
        return ok({"deleted": True})
    except Exception as e:
        return err(f"delete failed: {str(e)}", http_status=500)


@bp.route('/<int:exercise_id>', methods=['PUT'])
@token_required
def update_exercise(exercise_id: int):
    try:
        user_id = getattr(g, 'current_user_id', None)
        if not user_id:
            return err("missing user id", http_status=400)
        exercise = Exercise.query.get(exercise_id)
        if not exercise or exercise.created_by != int(user_id):
            return err("exercise not found", http_status=404)

        data = request.get_json(silent=True) or {}
        content = (data.get("content") or "").strip()
        title = data.get("title") or exercise.title
        meta = data.get("meta") or {}

        if meta:
            description = f"__META__{json.dumps(meta, ensure_ascii=False)}__\n" + content
        else:
            description = content

        exercise.title = title
        exercise.description = description
        new_content_json = exercise.content_json
        cleaned = (content or "").strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.replace("```json", "").replace("```", "").strip()
        if cleaned.startswith("{") and cleaned.endswith("}"):
            try:
                parsed = json.loads(cleaned)
                if isinstance(parsed, dict):
                    new_content_json = json.dumps(parsed, ensure_ascii=False)
            except Exception:
                pass
        exercise.content_json = new_content_json
        from app.extensions import db
        db.session.commit()
        return ok({"updated": True})
    except Exception as e:
        return err(f"save failed: {str(e)}", http_status=500)
