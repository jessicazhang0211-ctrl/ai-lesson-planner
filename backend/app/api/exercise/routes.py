# app/api/exercise/routes.py
from flask import Blueprint, request
from app.utils.response import ok, err
from app.models import user as user_model
from app import Config
import google.generativeai as genai

genai.configure(api_key=Config.GEMINI_API_KEY)

bp = Blueprint("exercise", __name__, url_prefix="/api/exercise")


@bp.route("/generate", methods=["POST", "OPTIONS"])
def generate_exercise():
    if request.method == "OPTIONS":
        return ok({"msg": "CORS preflight ok"})
    try:
        data = request.get_json()
        user_id = request.headers.get("X-User-Id")
        if not user_id:
            return err("缺少用户ID", http_status=400)
        # 构建AI prompt
        prompt = f"请根据以下信息生成{data.get('count', 10)}道{data.get('difficulty', '中等')}难度的{data.get('subject', '数学')}习题，题型包括{','.join(data.get('types', []))}，知识点/主题为：{data.get('topic', '')}，并{'包含答案解析' if data.get('includeAnswer', 'yes') == 'yes' else '不包含答案解析'}。"
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        content = response.text.strip()
        # TODO: 存档到数据库（可选）
        return ok({"content": content})
    except Exception as e:
        return err(f"AI 生成失败: {str(e)}", http_status=500)

@bp.route("/history", methods=["GET"])
def exercise_history():
    try:
        user_id = request.headers.get("X-User-Id")
        if not user_id:
            return err("缺少用户ID", http_status=400)
        # TODO: 查询数据库返回历史记录
        return ok([])
    except Exception as e:
        return err(f"历史获取失败: {str(e)}", http_status=500)
