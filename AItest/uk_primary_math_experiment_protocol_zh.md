# 英格兰小学数学 AI 备课实验执行手册

更新时间：2026-03-15

## 1. 已完成的任务资产

1. 研究主报告：uk_primary_math_ai_dissertation_research_report_zh.md
2. 模型行为约束：uk_primary_math_model_guardrails.json
3. 输出结构约束：uk_primary_math_lesson_plan_schema.json
4. 评估量表：uk_primary_math_evaluation_rubric.json
5. 模型测试矩阵：uk_primary_math_model_test_matrix.json
6. 单次请求示例：uk_primary_math_generation_request_example.json
7. 36 条标准任务集：uk_primary_math_task_set_36.json

## 2. 主实验设置

1. 任务集：36 tasks
2. 模型组：优先使用 model_test_matrix 中 core_experiment_set
3. 系统配置组：
- direct_prompting
- curriculum_grounded_rag
- rag_plus_age_aware_guardrails
4. 总生成量：36 x 8 x 3 = 864（推荐主实验规模）

## 3. 每次生成的最小记录字段

1. run_id
2. task_id
3. model_provider
4. model_name
5. system_condition
6. request_time
7. latency_ms
8. input_tokens
9. output_tokens
10. estimated_cost
11. raw_output
12. json_valid
13. schema_valid
14. safety_flags

## 4. 评估流程

1. 自动评估
- JSON 可解析检查
- Schema 校验
- 必填字段覆盖率
- British English 风格检查

2. 人工评估
- 评审人数：2 到 3 人
- 工具：uk_primary_math_evaluation_rubric.json
- 打分维度：7 个维度，1 到 5 分

3. 一致性处理
- 先独立打分
- 分歧 > 1 分的项进行复核讨论
- 记录最终共识分与备注

## 5. 结果分析输出建议

1. 每模型每配置的维度均分
2. JSON 有效率与 Schema 通过率
3. 幻觉与政策风险项频次
4. 平均延迟与成本对比
5. 代表性成功样例与失败样例

## 6. 论文落地对应关系

1. Chapter 3 System Design
- guardrails + schema + validation pipeline

2. Chapter 4 Methodology
- 36 任务构造 + 8 模型 + 3 配置

3. Chapter 5 Results
- 量化评分、有效率、成本时延

4. Chapter 6 Discussion
- 最优组合建议、失败模式与局限

## 7. 复现实验注意事项

1. 所有模型统一 en-GB 输出要求
2. 必须保存原始响应，避免仅保留后处理结果
3. 若模型版本更新，单独标注 run batch 版本
4. 预览模型单独分析，不与稳定模型直接下结论
