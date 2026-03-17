# AItest 下一步操作（含 API Key 放置位置）

## 1. 你现在要做什么（下一步）

1. 复制配置文件：把 AItest/.env.example 复制为 AItest/.env
2. 把你的 API Key 填入 AItest/.env
3. 运行批量实验脚本：

```powershell
D:/ai-lesson-planner/venv/Scripts/python.exe AItest/run_experiments.py
```

4. 结果会输出到：AItest/results/experiment_runs_*.csv

### 快速实验（推荐先跑）

```powershell
D:/ai-lesson-planner/venv/Scripts/python.exe AItest/run_quick_experiment.py
```

说明：
1. 默认只跑 1 条任务。
2. 默认只跑快模型子集，降低超时概率。
3. 跑完后继续执行 summarize_results.py 生成论文对比表。

5. 一键生成论文对比表：

```powershell
D:/ai-lesson-planner/venv/Scripts/python.exe AItest/summarize_results.py
```

会生成：
- AItest/results/summary_table_*.csv（可贴到论文表格）
- AItest/results/summary_report_*.md（可直接引用文字结论）

## 2. API Key 贴在哪里

你把 Key 粘贴到这个文件：

- AItest/.env

字段如下（等号后填你的真实 key）：

```env
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
GEMINI_API_KEY=your_gemini_key
DEEPSEEK_API_KEY=your_deepseek_key
QWEN_API_KEY=your_qwen_key
```

## 3. 如果你只测一个平台

例如只测 Gemini，只需要填：

```env
GEMINI_API_KEY=your_gemini_key
```

其他留空即可，脚本会自动跳过无 key 的模型并在 CSV 里标记 SKIPPED_NO_KEY。

## 4. 建议先做的小规模试跑

先跑 3 条任务验证流程：

```env
EXPERIMENT_MAX_TASKS=3
```

确认无误后改回 36。

## 5. 安全提醒

1. 不要把 AItest/.env 提交到公开仓库。
2. 不要把 key 放在前端 js 文件。
3. 如 key 泄露，立即在官方控制台撤销并重建。
