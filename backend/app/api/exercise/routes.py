# app/api/exercise/routes.py
from flask import Blueprint, request, g
from app.utils.response import ok, err
from app.models import Exercise
from app import Config
import google.generativeai as genai
from app.utils.auth import token_required
import json

genai.configure(api_key=Config.GEMINI_API_KEY)

bp = Blueprint("exercise", __name__, url_prefix="/api/exercise")


@bp.route("/generate", methods=["POST", "OPTIONS"])
@token_required
def generate_exercise():
    if request.method == "OPTIONS":
        return ok({"msg": "CORS preflight ok"})
    try:
        data = request.get_json()
        user_id = getattr(g, 'current_user_id', None)
        if not user_id:
            return err("缺少用户ID", http_status=400)
        # 构建AI prompt
        prompt = f"""
请根据以下信息生成{data.get('count', 10)}道{data.get('difficulty', '中等')}难度的{data.get('subject', '数学')}习题，题型包括{','.join(data.get('types', []))}，知识点/主题为：{data.get('topic', '')}。

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
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        content = response.text.strip()

        def _extract_json(text):
            if not text:
                return None
            cleaned = text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.replace("```json", "").replace("```", "").strip()
            try:
                return json.loads(cleaned)
            except Exception:
                pass
            # try to extract first JSON object/array in the response
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(cleaned[start:end + 1])
                except Exception:
                    return None
            start = cleaned.find("[")
            end = cleaned.rfind("]")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(cleaned[start:end + 1])
                except Exception:
                    return None
            return None

        structured = _extract_json(content)
        # 存档到数据库，前端参数信息一并序列化进description前缀
        from app.extensions import db
        import datetime, json
        meta = {
            'topic': data.get('topic', ''),
            'grade': data.get('grade', ''),
            'subject': data.get('subject', ''),
            'types': data.get('types', []),
            'difficulty': data.get('difficulty', ''),
            'count': data.get('count', ''),
            'includeAnswer': data.get('includeAnswer', '')
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
        db.session.commit()
        return ok({"content": content, "exercise_id": exercise.id})
    except Exception as e:
        return err(f"AI 生成失败: {str(e)}", http_status=500)


@bp.route("/history", methods=["GET"])
@token_required
def exercise_history():
    try:
        user_id = getattr(g, 'current_user_id', None)
        if not user_id:
            return err("缺少用户ID", http_status=400)
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
        return err(f"历史获取失败: {str(e)}", http_status=500)


@bp.route('/<int:exercise_id>', methods=['DELETE'])
@token_required
def delete_exercise(exercise_id: int):
    try:
        user_id = getattr(g, 'current_user_id', None)
        if not user_id:
            return err("缺少用户ID", http_status=400)
        exercise = Exercise.query.get(exercise_id)
        if not exercise or exercise.created_by != int(user_id):
            return err("exercise not found", http_status=404)
        from app.extensions import db
        db.session.delete(exercise)
        db.session.commit()
        return ok({"deleted": True})
    except Exception as e:
        return err(f"删除失败: {str(e)}", http_status=500)


@bp.route('/<int:exercise_id>', methods=['PUT'])
@token_required
def update_exercise(exercise_id: int):
    try:
        user_id = getattr(g, 'current_user_id', None)
        if not user_id:
            return err("缺少用户ID", http_status=400)
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
        exercise.content_json = None
        from app.extensions import db
        db.session.commit()
        return ok({"updated": True})
    except Exception as e:
        return err(f"保存失败: {str(e)}", http_status=500)
