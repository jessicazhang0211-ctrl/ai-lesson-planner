# app/api/lesson/routes.py
from flask import Blueprint, request, g
from app.utils.response import ok, err
import google.generativeai as genai
from app.config import Config

from app.extensions import db
from app.models.lesson import Lesson
from app.utils.auth import token_required
import datetime, json

bp = Blueprint("lesson", __name__, url_prefix="/api/lesson")

genai.configure(api_key=Config.GEMINI_API_KEY)


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
    objectives = data.get("objectives", "")
    key_points = data.get("key_points", "")
    activities = data.get("activities", "")

    if not topic:
        return err("topic is required", http_status=400)

    prompt = f"""
请根据以下信息生成一份结构化的教案：

年级：{grade}
学科：{subject}
课题：{topic}
课时：{duration} 分钟
节数：{lesson_count}
教学目标：{objectives}
重难点：{key_points}
教学活动：{activities}

教案格式要求：
一、基本信息
二、教学目标
三、重难点
四、教学过程
五、评价与反馈
六、作业设计

如果节数大于1，请按“第1课时/第2课时...”分节输出，每一节都包含上述六个部分。

请用中文生成完整教案。
"""

    try:
        if not Config.GEMINI_API_KEY:
            return err("Gemini API key not configured", http_status=500)
        
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        lesson_plan = response.text.strip()

        # 存档到数据库，序列化前端参数到 description 前缀
        meta = {
            'topic': topic,
            'grade': grade,
            'subject': subject,
            'duration': duration,
            'lesson_count': lesson_count,
            'objectives': objectives,
            'key_points': key_points,
            'activities': activities
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

        return ok({"lesson_plan": lesson_plan, "lesson_id": lesson.id})
    except Exception as e:
        print(f"Gemini error: {str(e)}")  # 调试日志
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