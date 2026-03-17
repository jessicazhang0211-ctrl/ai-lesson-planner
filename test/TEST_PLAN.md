# AI Lesson Planner 测试计划（毕业论文可用）

更新时间：2026-03-15
适用范围：本地开发环境（后端运行于 http://127.0.0.1:5000）

## 1. 测试目标

1. 验证系统核心闭环可用：教师注册/登录 -> 班级创建 -> 学生导入 -> 学生登录。
2. 验证关键权限规则：学生不能自助注册。
3. 验证基础接口稳定性：健康检查、用户信息、班级列表/详情、公共班级查询。

## 2. 测试范围

1. 认证模块：`/api/auth/*`
2. 用户模块：`/api/user/*`
3. 班级模块：`/api/class/*`
4. 学生端基础模块：`/api/student/assignments`

不纳入本次自动化的内容：
1. AI 生成教案/习题（依赖外部 Gemini Key 与模型配额）。
2. 教师评阅完整链路（需先有已发布习题与学生提交数据）。

## 3. 前置条件

1. 后端服务已启动：`backend/app.py`。
2. 数据库可连接。
3. 允许在数据库中创建测试数据（测试账号、测试班级、测试学生）。

## 4. 用例清单

1. `health_check`：健康检查接口返回 `status=ok`。
2. `teacher_register`：教师账号注册成功。
3. `teacher_login`：教师账号登录成功并拿到 token。
4. `student_self_register_blocked`：学生自助注册返回 403。
5. `create_class`：教师创建班级成功。
6. `list_classes`：教师查询班级列表成功且包含新建班级。
7. `get_class_detail`：班级详情可访问。
8. `list_public_classes`：公共班级列表可访问。
9. `teacher_overview`：教师总览接口返回结构化结果。
10. `import_students_json`：通过 JSON 导入学生成功，自动创建学生账号。
11. `student_login`：导入学生后可用学号+默认密码登录。
12. `student_assignments`：学生作业列表接口可访问。
13. `get_me`：教师可读取个人资料。
14. `update_me`：教师可更新个人资料。
15. `change_password_and_relogin`：修改密码并重新登录成功。

## 5. 执行方式

1. 启动后端服务。
2. 在项目根目录执行：

```powershell
D:/ai-lesson-planner/venv/Scripts/python.exe test/run_all_tests.py
```

3. 查看输出摘要与 `test/TEST_REPORT.md`。

## 6. 判定标准

1. 所有必测用例 `PASS`。
2. 失败用例需给出错误信息与复现接口。
3. 总结报告可直接用于论文“系统测试”章节。
