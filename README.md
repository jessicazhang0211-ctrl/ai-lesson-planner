# AI Lesson Planner

基于 Flask + MySQL + 原生前端的教学辅助系统，包含教师端与学生端。

## 1. 当前业务规则（重要）

1. 教师使用邮箱 + 密码登录。
2. 学生使用学号 + 密码登录。
3. 学生不允许自助注册。
4. 教师导入学生时会自动创建学生账号，初始密码统一为 123456。
5. 导入时学号可留空，系统会自动生成学号：
   YYYY + 0 + 班级两位 + 该班三位序号
   例如：2026003001

## 2. 项目结构

```text
backend/
  app.py                    # 后端启动入口
  requirements.txt
  app/
    __init__.py             # create_app
    config.py               # 读取 .env，构建 SQLAlchemy 配置
    api/                    # 路由模块
    models/                 # 数据模型
frontend/
  login.html                # 教师登录页
  teacher/                  # 教师端页面
  student/                  # 学生端页面
```

## 3. 环境要求

1. Python 3.10+
2. MySQL 5.7+/8.0+
3. Windows / macOS / Linux 均可

Python 依赖见 backend/requirements.txt：

- flask
- flask-cors
- flask-sqlalchemy
- python-dotenv
- pymysql
- werkzeug
- google-generativeai
- openpyxl
- xlrd
- PyJWT

## 4. 后端启动

### 4.1 Windows PowerShell

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

### 4.2 Linux / macOS / WSL

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

默认地址：

- http://127.0.0.1:5000

健康检查：

- GET /api/health

## 5. 前端启动

前端为静态页面，建议用静态服务运行，不要直接 file:// 打开。

```bash
cd frontend
python -m http.server 8000
```

常用页面：

1. 教师登录：http://127.0.0.1:8000/login.html
2. 教师首页：http://127.0.0.1:8000/teacher/index.html
3. 学生登录：http://127.0.0.1:8000/student/login.html

## 6. 配置文件 backend/.env

示例：

```ini
FLASK_ENV=development
SECRET_KEY=dev-secret-change-me

DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=ai_lesson_planner
DB_USER=root
DB_PASSWORD=your_password

# 可选
GEMINI_API_KEY=
JWT_SECRET=dev-secret-change-me
JWT_ALGORITHM=HS256
JWT_EXP_SECONDS=3600
ENABLE_GLOBAL_ERROR_HANDLER=0
```

注意：

1. 请不要把真实密钥和密码提交到仓库。
2. backend/.env 中仅保留 KEY=VALUE 格式内容。
3. 项目启动时会执行 db.create_all()（开发环境方便，生产建议改迁移方案）。

## 7. 认证说明

### 7.1 教师注册与登录

1. 教师注册：POST /api/auth/register
2. 教师登录：POST /api/auth/login（email + password）

### 7.2 学生登录

1. 学生登录：POST /api/auth/login（stu_id + password）
2. 学生注册接口已禁用（role=student 返回 403）

登录成功后会返回 token。前端会在请求中携带：

1. Authorization: Bearer <token>
2. X-User-Id（兼容旧逻辑）

## 8. 班级与导入说明

### 8.1 创建班级

接口：POST /api/class/

请求体示例：

```json
{
  "name": "高一(3)班",
  "desc": "数学强化班"
}
```

### 8.2 导入学生

接口：POST /api/class/<cid>/import

支持：

1. xlsx
2. xls
3. csv
4. JSON students 数组

当前最小必需列：

1. name 或 姓名

可选列：

1. stu_id / 学号（可空）
2. parent_phone / 家长电话
3. status / 状态

学号自动生成规则（导入新增时）：

1. 前缀：YYYY0CC
2. YYYY 为当年年份
3. CC 为班级 ID 的后两位（不足补 0）
4. NNN 为该班三位递增序号（001-999）

导入响应会返回：

1. added
2. updated
3. account_created（本次自动创建账号数）

## 9. 常见问题

### Q1：创建班级失败

排查顺序：

1. 先确认后端是否正常运行（/api/health）。
2. 确认浏览器 localStorage 有 login_user 和 auth_token。
3. 重新登录一次教师账号，确保 login_user 里有 id。
4. 查看后端日志中的 message（例如 missing X-User-Id / invalid user）。

### Q2：学生无法登录

排查顺序：

1. 使用学号登录，不是姓名。
2. 密码默认 123456（若未重置）。
3. 确认该学生已导入且已生成 StudentProfile。

### Q3：导入提示表头错误

1. 至少保证有 name 或 姓名 列。
2. 建议使用系统模板，避免隐藏字符/BOM 干扰。

## 10. 开发建议

1. 增加 .gitignore，忽略 __pycache__、.pyc、.env。
2. 生产环境建议引入 Flask-Migrate，替代 db.create_all。
3. 建议补齐 pytest 用例，覆盖登录、创建班级、导入学生。

## 11. AItest 论文重测流程（2026-03-16）

本节对应 AItest 目录下英国小学数学论文实验，按报告要求执行：

1. 36 tasks
2. 8 models
3. 3 conditions（direct prompting / curriculum grounded rag / rag plus age aware guardrails）

### 11.1 主实验命令

```powershell
D:/ai-lesson-planner/venv/Scripts/python.exe AItest/run_report_required_experiment.py
```

### 11.2 已修复兼容性问题

OpenAI GPT-5 系列在 chat/completions 下不支持 max_tokens，需使用 max_completion_tokens。

修复位置：

1. AItest/run_experiments.py
2. call_openai_like 增加 token_param_name 参数
3. OpenAI 分支显式传入 max_completion_tokens

### 11.3 本次完整重测结果

最终汇总以 fixed 标签结果为准：

1. 实验明细 CSV：AItest/results/experiment_runs_report_required_fixed_20260316_034426.csv
2. 论文表格 CSV：AItest/results/summary_table_report_required_fixed_20260316_034438.csv
3. 自动汇总报告：AItest/results/summary_report_report_required_fixed_20260316_034438.md

关键统计：

1. 总运行数 864
2. HTTP 成功数 864
3. JSON-like 比例 100.0%

### 11.4 复现建议

1. 先验证 AItest/.env 中各平台 key 可用。
2. 若后续再次全量测试，建议先跑 1 个模型冒烟，再跑全量。
3. summarize_results.py 默认取最新 experiment_runs_*.csv；如需固定批次，设置 EXPERIMENT_RUN_TAG 后再汇总。

