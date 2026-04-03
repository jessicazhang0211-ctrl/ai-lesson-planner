# AI Lesson Planner

基于 Flask + MySQL + 原生前端的 AI 教学辅助平台，包含教师端、学生端与 AItest 多模型评测子系统。

本 README 按“完整项目文档”框架重写，覆盖：软件定位、运行方式、使用说明、目录结构、常见问题、版本历史、贡献与法律声明等。

## 1. 软件定位与基本功能

### 1.1 软件定位

本项目面向小学数学教学场景，提供从“教学资源生成 -> 发布 -> 学生作答 -> 评分反馈 -> 数据分析”的完整闭环。

### 1.2 核心角色

1. 教师：邮箱登录，创建班级、导入学生、生成并发布教案/习题、评阅作业。
2. 学生：学号登录，查看任务、完成作答、查看成绩与分析。

### 1.3 核心功能

1. 教师注册登录与 JWT 鉴权。
2. 班级管理与学生批量导入（Excel/CSV/JSON）。
3. 教案与习题 AI 生成（支持 Gemini/OpenAI）。
4. 资源发布、作业提交、评分与评语。
5. 班级统计与学生学情分析。
6. AItest 子系统用于论文实验与模型对比评测。

### 1.4 关键业务规则

1. 学生不允许自助注册。
2. 教师导入学生后自动建账号，默认密码为 123456。
3. 学生首次登录需改密。
4. 学号支持自动生成（按年份 + 班级 + 序号规则）。

## 2. 项目与子模块说明

### 2.1 主项目名称

- AI Lesson Planner

### 2.2 子模块与库

1. backend：Flask 后端 API 与业务逻辑。
2. frontend：静态页面前端（教师端/学生端）。
3. AItest：多模型生成质量评测与论文实验脚本。
4. test：自动化测试、合规检查与提示词测试数据。

## 3. 环境依赖

### 3.1 系统依赖

1. Python 3.10+
2. MySQL 5.7+ 或 8.0+
3. Windows/macOS/Linux（推荐在虚拟环境中运行）

### 3.2 Python 依赖

依赖文件：backend/requirements.txt

```txt
flask
flask-cors
flask-sqlalchemy
python-dotenv
pymysql
werkzeug
google-generativeai
openpyxl
xlrd
PyJWT
python-docx
```

## 4. 安装、配置与运行指南

### 4.1 后端安装与启动

Windows PowerShell：

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Linux/macOS：

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

### 4.2 前端启动

前端是静态页面，建议通过静态服务启动：

```bash
cd frontend
python -m http.server 8000
```

常用入口：

1. 教师登录：http://127.0.0.1:8000/login.html
2. 教师首页：http://127.0.0.1:8000/teacher/index.html
3. 学生登录：http://127.0.0.1:8000/student/login.html

### 4.3 配置说明（backend/.env）

```ini
FLASK_ENV=development
SECRET_KEY=dev-secret-change-me

DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=ai_lesson_planner
DB_USER=root
DB_PASSWORD=your_password

GEMINI_API_KEY=
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1

LESSON_GENERATION_MODEL=gpt-5-mini
EXERCISE_GENERATION_MODEL=gemini-2.5-flash
LESSON_MAX_COMPLETION_TOKENS=12000

JWT_SECRET=dev-secret-change-me
JWT_ALGORITHM=HS256
JWT_EXP_SECONDS=3600
ENABLE_GLOBAL_ERROR_HANDLER=0
```

注意：

1. 不要提交真实密钥到仓库。
2. 开发环境默认启动时执行 db.create_all()。

## 5. 简要使用说明

### 5.1 教师端流程

1. 注册/登录教师账号。
2. 创建班级。
3. 导入学生名单（可不填学号，系统自动生成）。
4. 生成教案/习题并发布。
5. 查看学生提交并进行评分反馈。

### 5.2 学生端流程

1. 使用学号 + 默认密码登录。
2. 首次登录修改密码。
3. 查看作业并提交答案。
4. 查看成绩、评语和分析。

## 6. 5 行快速体验

如需最小化体验后端 API：

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

启动后访问：http://127.0.0.1:5000/api/health

## 7. 抓取最新代码与构建说明

### 7.1 抓取最新代码

```bash
git clone <your-repo-url>
cd ai-lesson-planner
git pull
```

### 7.2 构建说明

1. 后端为 Python 项目，无额外前端打包步骤。
2. 前端为静态页面，使用 python -m http.server 即可运行。

## 8. 代码目录结构与基本原理

```text
ai-lesson-planner/
├── backend/                     # Flask 后端
│   ├── app.py                   # 启动入口
│   ├── requirements.txt         # 依赖
│   ├── app/
│   │   ├── __init__.py          # create_app、CORS、路由注册
│   │   ├── config.py            # 环境变量与数据库配置
│   │   ├── api/                 # 认证、班级、教案、习题、资源、学生接口
│   │   ├── models/              # 数据模型
│   │   ├── services/            # AI 调用与业务服务
│   │   └── utils/               # 鉴权、响应封装、JSON 处理等
│   └── scripts/                 # 辅助脚本
├── frontend/                    # 静态前端
│   ├── login.html               # 登录页
│   ├── register.html            # 注册页
│   ├── teacher/                 # 教师端页面与脚本
│   ├── student/                 # 学生端页面与脚本
│   ├── css/                     # 公共样式
│   └── js/                      # 公共脚本
├── AItest/                      # 多模型评测子系统
│   ├── run_experiments.py       # 全量实验
│   ├── run_quick_experiment.py  # 快速实验
│   ├── summarize_results.py     # 结果汇总
│   ├── HOW_TO_RUN_ZH.md         # AItest 运行文档
│   └── results/                 # 评测输出
└── test/                        # 自动化测试与合规文档
```

基本原理：

1. 前端发起 API 请求到 backend。
2. backend 使用 JWT 校验身份并执行业务逻辑。
3. AI 内容生成由 services 层调用第三方模型接口。
4. 结果存入 MySQL，前端再读取并展示。

## 9. 测试与实验指引

### 9.1 自动化测试

```powershell
python test/run_all_tests.py
```

测试报告输出到：test/TEST_REPORT.md

### 9.2 AItest 实验

先准备 AItest/.env（可参考 AItest/.env.example），然后执行：

```powershell
D:/ai-lesson-planner/venv/Scripts/python.exe AItest/run_quick_experiment.py
D:/ai-lesson-planner/venv/Scripts/python.exe AItest/run_experiments.py
D:/ai-lesson-planner/venv/Scripts/python.exe AItest/summarize_results.py
```

详细说明见：AItest/HOW_TO_RUN_ZH.md

## 10. 常见问题说明（FAQ）

1. 教师创建班级失败。
  检查后端是否可访问 /api/health，确认 token 与 X-User-Id 是否有效。

2. 学生无法登录。
  确认使用学号登录；默认密码为 123456；首次登录后需修改密码。

3. 导入学生失败。
  确保至少包含 name 或 姓名列，文件格式为 xlsx/xls/csv 或 JSON students 数组。

4. 跨域报错（CORS）。
  检查 backend/app/config.py 中 CORS_ORIGINS 配置。

5. AI 生成为空或超时。
  检查 API Key、配额、网络与超时设置。

## 11. 版本历史（简）

### v0.3.0（2026-04-03）

1. README 按完整项目规范重构。
2. 明确项目模块、运行方式、测试与实验流程。
3. 增补贡献、联系、法律声明与已知缺口。

### v0.2.x（历史）

1. 完成教师/学生双端基础业务闭环。
2. 引入 AItest 多模型评测流程。

## 12. 提交 Bug、功能请求与补丁

当前建议流程：

1. 提交 Issue：描述现象、复现步骤、期望结果、环境信息。
2. 提交补丁：新建分支 -> 提交修改 -> 发起 Pull Request。
3. 功能请求：说明教学场景、用户角色、接口影响面。

建议 Issue 模板包含：

1. 标题
2. 复现步骤
3. 实际结果
4. 期望结果
5. 日志/截图

## 13. 文档抓取与参考入口

1. 系统架构文档：SYSTEM_ARCHITECTURE.md
2. AItest 运行文档：AItest/HOW_TO_RUN_ZH.md
3. 测试计划：test/TEST_PLAN.md
4. 测试报告：test/TEST_REPORT.md
5. 合规文档：test/COMPLIANCE_GDPR_UK_ETHICS.md

## 14. 作者与联系信息

当前仓库未单独提供 AUTHORS 文件，可在此临时维护：

1. 项目维护者：待补充
2. 联系邮箱：jessicazhang0211@gmail.com
3. 项目主页：待补充

## 15. 版权、许可与法律声明

### 15.1 版权与许可

当前仓库暂未提供 LICENSE 文件。

建议：尽快补充开源许可证（如 MIT/Apache-2.0）并在根目录新增 LICENSE。

### 15.2 法律声明

1. 本项目涉及教育数据与第三方 AI 服务调用，使用前请确保符合所在地法律法规。
2. 若涉及真实学生数据，请遵守 GDPR/隐私保护要求并完成必要伦理审批。
3. 第三方模型接口的条款、费用与可用性由各供应商决定。

## 16. 已知缺口与后续计划

1. 补齐 LICENSE、CONTRIBUTING、CHANGELOG、AUTHORS。
2. 增加生产部署文档（Docker、迁移、监控）。
3. 增加 OpenAPI 文档与 CI 自动测试。
4. 增补 GDPR 数据导出/删除等合规接口。

