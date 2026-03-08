# app/api/exercise/routes.py
from flask import Blueprint, request, g
from app.utils.response import ok, err
from app.models import Exercise
from app import Config
import google.generativeai as genai
from app.utils.auth import token_required

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
        prompt = f"请根据以下信息生成{data.get('count', 10)}道{data.get('difficulty', '中等')}难度的{data.get('subject', '数学')}习题，题型包括{','.join(data.get('types', []))}，知识点/主题为：{data.get('topic', '')}，并{'包含答案解析' if data.get('includeAnswer', 'yes') == 'yes' else '不包含答案解析'}。"
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        content = response.text.strip()
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
        exercise = Exercise(
            title=data.get('topic', '') or '习题',
            description=description,
            created_by=int(user_id),
            created_at=datetime.datetime.now()
        )
        db.session.add(exercise)
        db.session.commit()
        return ok({"content": content})
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
