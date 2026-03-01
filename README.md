AI Lesson Planner

项目启动方法（在文件顶部）

后端（Windows PowerShell 示例）

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
# 在开发环境下直接运行 Flask 应用
python app.py
```

后端（使用 Unix / WSL / Git Bash）

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

说明：
- 运行后默认监听 http://127.0.0.1:5000（参见 backend/app.py）。
- 若需要使用 MySQL，请在 backend/.env 中配置数据库连接（下面有示例）。

前端（静态页面）

前端是纯静态 HTML/CSS/JS，直接用浏览器打开 frontend/login.html / frontend/teacher/index.html 等即可。也可以用一个简单的静态服务器在本地预览：

```bash
# 在 frontend 目录运行（默认 8000 端口）：
cd frontend
python -m http.server 8000
# 浏览器访问 http://127.0.0.1:8000/teacher/index.html
```

环境变量示例（backend/.env）

在 backend 目录创建 .env 文件，示例：

```ini
# 数据库（按需修改）
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=ai_lesson_planner
DB_USER=root
DB_PASSWORD=your_db_password

# 可选：Google Gemini / Generative API key（用于 AI 相关功能）
GEMINI_API_KEY=your_api_key_here

# 可选的 Flask secret
SECRET_KEY=dev-secret
```

注意：配置完成后，应用启动时会在首次运行时自动创建表（db.create_all()，仅用于开发）。

运行内置测试脚本

后端启动后，可以运行仓库中的简单测试脚本：

```bash
# 在另一个终端，确保后端已运行
python backend/test_api.py
```

该脚本会尝试注册/登录、创建班级、学员加入等接口调用，用于快速验证 API 是否可用。

依赖

- Python 依赖见 backend/requirements.txt（主要包括 flask, flask-sqlalchemy, pymysql, google-generativeai 等）。

项目结构（简要）

- backend/: Flask 后端源码
  - app.py：启动入口
  - app/: 应用包（路由、模型、配置等）
- frontend/: 静态前端页面（登录、注册、教师端页面等）

开发提示

- 若使用 MySQL，请先创建数据库（名与 .env 中 DB_NAME 一致），并确保数据库用户有权限。
- AI 功能依赖 GEMINI_API_KEY，若未配置则相关接口会退回到无 AI 的逻辑或报错。

联系 / 贡献

如果需要我帮你：
- 运行项目并调试错误
- 添加 Dockerfile 或更完善的部署说明

欢迎告诉我接下来希望我做什么（例如：运行测试、添加 Docker 支持、或将后端改为使用 Flask-Migrate）。
