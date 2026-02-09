# app/api/lesson/routes.py
from flask import Blueprint, request
from app.utils.response import ok, err
import google.generativeai as genai
from app.config import Config

bp = Blueprint("lesson", __name__, url_prefix="/api/lesson")

genai.configure(api_key=Config.GEMINI_API_KEY)

@bp.route("/generate", methods=["POST", "OPTIONS"])
def generate_lesson():
    if request.method == "OPTIONS":
        return "", 204

    data = request.get_json(silent=True) or {}
    grade = data.get("grade", "")
    subject = data.get("subject", "")
    topic = data.get("topic", "")
    duration = data.get("duration", "")
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

请用中文生成完整教案。
"""

    try:
        if not Config.GEMINI_API_KEY:
            return err("Gemini API key not configured", http_status=500)
        
        # 使用最新的免费模型
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        lesson_plan = response.text.strip()
        
        return ok({"lesson_plan": lesson_plan})
    except Exception as e:
        print(f"Gemini error: {str(e)}")  # 调试日志
        return err(f"AI 生成失败: {str(e)}", http_status=500)