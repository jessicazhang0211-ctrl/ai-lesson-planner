# AI Lesson Planner 系统架构图

> 基于当前代码结构生成（Flask + MySQL + 静态前端 + AItest评测流水线）

```mermaid
flowchart TB
  %% ======================
  %% Main Product System
  %% ======================
  subgraph U[用户层]
    T[教师]
    S[学生]
  end

  subgraph F[前端层 - frontend]
    L[登录与注册页面\nlogin.html / register.html]
    TP[教师端页面\nfrontend/teacher]
    SP[学生端页面\nfrontend/student]
    JS[页面脚本与资源\nfrontend/js + assets + css]
  end

  subgraph B[后端 API 层 - Flask]
    APP[应用入口\nbackend/app.py -> create_app]
    BP[蓝图路由\nauth user class lesson exercise resource student]
    MW[中间件\nJWT鉴权 token_required\n全局错误处理(可选)]
    SVC[服务层\nai_service / resource_service]
    REPO[仓储层\nrepositories]
    ORM[模型层\nSQLAlchemy models]
  end

  subgraph D[数据与外部服务]
    DB[(MySQL\nai_lesson_planner)]
    GEM[Gemini API\n教案生成]
  end

  T --> L
  T --> TP
  S --> SP
  L --> JS
  TP --> JS
  SP --> JS

  JS -->|HTTP /api/*| APP
  APP --> BP
  BP --> MW
  MW --> SVC
  MW --> REPO
  REPO --> ORM
  ORM --> DB
  SVC --> GEM

  %% ======================
  %% AItest Subsystem
  %% ======================
  subgraph X[AItest 评测子系统]
    CFG[实验配置资产\ntask_set / model_matrix / request_template / guardrails / .env]
    RUN[执行脚本\nrun_experiments.py\nrun_report_required_experiment.py]
    CALL[多厂商模型调用适配\nOpenAI / Anthropic / Gemini / DeepSeek / Qwen]
    JUDGE[评测与复测\nretest_with_rubric.py\nEVAL_JUDGE_MODEL]
    OUT[结果产物\nAItest/results/*.csv *.md]
  end

  CFG --> RUN
  RUN --> CALL
  CALL --> OUT
  OUT --> JUDGE
  JUDGE --> OUT
```

## 说明

1. 主系统采用前后端分离：前端静态页面通过 HTTP 调用 Flask 的 `/api/*`。
2. 后端以蓝图组织业务域，数据访问经 SQLAlchemy 落到 MySQL。
3. 教案 AI 生成在服务层调用 Gemini API，结果同时返回前端并写入数据库历史。
4. AItest 为独立实验流水线，不依赖前端，直接读取任务/模型矩阵后批量调用模型并输出可复现实验结果。
