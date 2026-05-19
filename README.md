# AI Lesson Planner

AI Lesson Planner 是一个面向教学场景的 AI 备课与学习管理系统。项目包含教师端、学生端、Flask 后端 API、Vite/React 前端壳层，以及用于论文/实验的 AI 模型评测脚本。

## 功能概览

- 教师注册、登录、个人资料与密码管理
- 班级创建、学生导入、班级统计与学生账号管理
- AI 教案生成、历史记录、版本回滚与验证日志
- AI 习题生成、自适应练习、变式题与发布
- 教学资源发布、学生提交、教师评阅与 AI 摘要
- 学生作业、练习、错题回顾、成绩与学习分析
- 知识库导入与资源/知识点统计
- AI 模型对比实验、自动化测试用例与论文辅助报告

## 技术栈

- 后端：Python、Flask、Flask-SQLAlchemy、PyMySQL、Flask-CORS、PyJWT、python-dotenv
- 数据库：MySQL，字符集建议使用 `utf8mb4`
- AI 服务：OpenAI API 用于教案生成，Google Gemini 用于习题/通用文本生成
- 前端：Vite、React、React Router、Lucide React，并兼容已有静态 HTML/CSS/JS 页面
- 测试与实验：Python 脚本、JSON/CSV 测试数据、OpenPyXL、Matplotlib

## 目录结构

```text
.
├── backend/                 # Flask 后端
│   ├── app.py               # 后端启动入口
│   ├── requirements.txt     # Python 依赖
│   ├── app/
│   │   ├── api/             # 认证、用户、教案、习题、班级、资源、学生接口
│   │   ├── models/          # SQLAlchemy 数据模型
│   │   ├── services/        # AI、资源、知识库、诊断等业务服务
│   │   ├── schemas/         # 结构化数据 schema
│   │   └── utils/           # 认证、响应、JSON 处理工具
│   └── scripts/             # 辅助脚本
├── frontend/                # Vite/React 前端
│   ├── src/                 # React 应用壳层与共享组件
│   ├── teacher/             # 教师端静态页面
│   ├── student/             # 学生端静态页面
│   ├── css/ js/ assets/     # 公共静态资源
│   └── package.json
├── test/                    # 自动化测试、测试计划与提示词测试数据
├── AItest/                  # AI 模型评测、论文实验与统计脚本
└── *.xlsx                   # 功能测试清单
```

## 环境要求

- Python 3.10+
- Node.js 20+（用于 Vite 前端）
- MySQL 8 或兼容版本
- 可用的 OpenAI / Gemini API Key（仅 AI 生成功能需要）

## 后端配置

1. 创建数据库：

```sql
CREATE DATABASE ai_lesson_planner CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

2. 在 `backend/.env` 中配置环境变量：

```env
SECRET_KEY=dev-secret
JWT_SECRET=dev-secret

DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=ai_lesson_planner
DB_USER=root
DB_PASSWORD=

OPENAI_API_KEY=your_openai_key
OPENAI_BASE_URL=https://api.openai.com/v1
LESSON_GENERATION_MODEL=gpt-5-mini
LESSON_MAX_COMPLETION_TOKENS=12000
OPENAI_TIMEOUT_SECONDS=300
OPENAI_RETRY_COUNT=1

GEMINI_API_KEY=your_gemini_key
EXERCISE_GENERATION_MODEL=gemini-2.5-flash

CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
FLASK_DEBUG=1
FLASK_USE_RELOADER=0
```

说明：后端启动时会调用 `db.create_all()` 自动创建数据表，并补齐部分旧表字段。

## 启动后端

在项目根目录执行：

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
python backend\app.py
```

默认服务地址：

```text
http://127.0.0.1:5000
```

健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:5000/api/health
```

预期返回：

```json
{"status":"ok"}
```

## 启动前端

```powershell
cd frontend
npm install
npm run dev
```

默认访问地址：

```text
http://127.0.0.1:5173
```

常用入口：

- 教师登录：`/login`
- 教师工作台：`/teacher`
- 学生登录：`/student/login`
- 学生工作台：`/student`

前端默认 API 地址为 `http://127.0.0.1:5000`。如需修改，可设置：

```env
VITE_API_BASE_URL=http://127.0.0.1:5000
```

## 构建前端

```powershell
cd frontend
npm run build
npm run preview
```

构建时会把 `assets`、`css`、`js`、`teacher`、`student`、`login.html`、`register.html` 等旧版静态资源复制到 `dist`。

## 自动化测试

先启动后端，并确保数据库可写，然后在项目根目录执行：

```powershell
.\venv\Scripts\python.exe test\run_all_tests.py
```

测试覆盖核心闭环：

- 健康检查
- 教师注册/登录
- 学生自助注册拦截
- 班级创建、查询、详情、公共班级列表
- 学生导入与学生登录
- 学生作业列表
- 用户资料读取、更新与改密

报告会输出到：

```text
test/TEST_REPORT.md
```

## Prompt 测试数据

`test/` 目录中包含教案生成和习题生成的提示词测试集：

- `LESSON_PROMPT_TEST_CASES_20.json`
- `EXERCISE_PROMPT_TEST_CASES_20.json`
- `PROMPT_TEST_USAGE.md`

目标接口：

- `POST /api/lesson/generate`
- `POST /api/exercise/generate`

## AI 模型实验

`AItest/` 目录用于批量评测不同模型在小学数学教案/任务生成中的表现。

先在 `AItest/.env` 中配置需要测试的平台 Key：

```env
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
GEMINI_API_KEY=your_gemini_key
DEEPSEEK_API_KEY=your_deepseek_key
QWEN_API_KEY=your_qwen_key
```

快速实验：

```powershell
.\venv\Scripts\python.exe AItest\run_quick_experiment.py
```

完整实验：

```powershell
.\venv\Scripts\python.exe AItest\run_experiments.py
```

生成汇总结果：

```powershell
.\venv\Scripts\python.exe AItest\summarize_results.py
```

输出通常位于：

```text
AItest/results/
```

## 常见问题

### 数据库连接失败

检查 `backend/.env` 中的 `DB_HOST`、`DB_PORT`、`DB_NAME`、`DB_USER`、`DB_PASSWORD` 是否正确，并确认 MySQL 服务已启动。

### 前端请求失败或 CORS 报错

确认后端已启动，并检查：

- 前端的 `VITE_API_BASE_URL`
- 后端的 `CORS_ORIGINS`
- 浏览器访问地址是否与 CORS 白名单匹配

### AI 生成功能不可用

教案生成依赖 `OPENAI_API_KEY`，习题和部分分析能力依赖 `GEMINI_API_KEY`。如果只测试基础业务链路，可以暂时不配置 API Key。

### 表结构不完整

开发环境下后端启动会自动创建表，并补齐 `student_profiles`、`lessons` 的部分字段。如生产环境需要更严格的版本管理，建议补充迁移工具。

## 安全提醒

- 不要提交 `backend/.env`、`AItest/.env` 或任何真实 API Key
- 不要把 API Key 写入前端 JS 文件
- 数据库密码、JWT 密钥和第三方 API Key 应在部署环境中单独配置

