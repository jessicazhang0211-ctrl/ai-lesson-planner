启动后端（MySQL 版）
cd G:\jessica_Workspace\ai-lesson-planner\backend
venv\Scripts\Activate.ps1
python wsgi.py


看到：

Running on http://127.0.0.1:5000

MySQL 里会自动出现 users 表（因为我们 db.create_all()）