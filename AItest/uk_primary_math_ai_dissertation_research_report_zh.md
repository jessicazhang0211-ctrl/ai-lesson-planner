# 基于英国小学数学的 AI 辅助备课系统研究报告（英方毕设版）

## 1. 项目定位

本项目建议定位为：

**A curriculum-grounded AI lesson planning assistant for primary mathematics in England**

中文可写为：

**面向英格兰小学数学课程的课程对齐型 AI 辅助备课系统设计与评估**

这个定位比“儿童直接使用的 AI 数学老师”更适合作为英国本科/硕士毕设，因为它有三个明显优点：

1. **研究边界更清楚**：主要服务对象是教师或师范生，核心任务是“备课、改写、差异化和结构化输出”。
2. **伦理风险更可控**：减少与低年龄儿童直接对话所带来的 safeguarding、隐私、误导和依赖风险。
3. **更容易做实验**：你可以让同一批提示在不同模型和不同系统配置下输出，再用人工量表评估课程对齐、可教性、年龄适配、结构合规、成本和速度。

---

## 2. 为什么必须按英国语境来做

如果你的毕设主要面向英国，那么系统设计不能只讲“通用教学”，而要明确写成：

- **课程依据**：英格兰 National Curriculum for Mathematics
- **教学依据**：DfE KS1/KS2 非法定数学指导、NCETM mastery 理念、EEF 数学教学证据
- **学校安全依据**：KCSIE、DfE 生成式 AI 产品安全要求
- **儿童数据依据**：ICO Children’s code
- **研究伦理依据**：BERA 教育研究伦理指南

也就是说，你的系统不是“随便生成教案”，而是要证明它：

- 能对齐英国小学数学课程；
- 能符合低年龄儿童的认知特点；
- 能满足英国学校环境对安全、隐私和教师监督的要求；
- 能输出可验证、可比较、可评估的结构化结果。

---

## 3. 建议论文题目（可直接选）

### 题目 1（最稳）
**Design and Evaluation of a Curriculum-Grounded AI Lesson Planning Assistant for Primary Mathematics in England**

### 题目 2（更强调儿童认知）
**Designing an Age-Appropriate AI-Assisted Lesson Preparation System for Primary Mathematics in England**

### 题目 3（更强调比较实验）
**Evaluating Large Language Models for AI-Assisted Primary Mathematics Lesson Planning in the English Curriculum Context**

如果你想让毕设既有系统设计，也有模型比较，最推荐把题目 1 和题目 3 合并成“系统 + 实验评估”的结构。

---

## 4. 核心研究目标

建议写成 3 个层次：

### 4.1 系统目标
设计一个面向教师的 AI 辅助备课系统，能够根据英格兰小学数学课程，生成：

- 课时目标
- 成功标准
- 先备知识
- 典型误区
- 表征与教具建议
- 教师提问脚本
- 分层任务
- formative assessment
- 差异化支持
- 输出为标准 JSON

### 4.2 教育目标
降低教师在以下任务上的时间成本：

- 从课程标准到课时设计的映射
- 同一知识点的不同年龄适配改写
- 误区预测与诊断题设计
- SEND / EAL / mixed attainment 的初步差异化
- 英式课堂语境下的表述统一（British English）

### 4.3 研究目标
评估不同 AI 模型和不同系统配置对以下指标的影响：

- curriculum alignment
- pedagogical quality
- age appropriateness
- misconception handling
- structured JSON validity
- latency
- token cost
- hallucination / unsupported claims
- British English consistency

---

## 5. 你的研究问题（Research Questions）

下面这组 RQ 很适合英方毕设：

### RQ1
**To what extent can a curriculum-grounded AI system generate primary mathematics lesson plans that align with the England mathematics curriculum and mastery-oriented pedagogy?**

### RQ2
**Does adding age-aware pedagogical constraints improve the suitability of generated lesson plans for younger primary learners?**

### RQ3
**How do different AI models compare in curriculum alignment, pedagogical usefulness, safety compliance, output validity, cost, and latency?**

### RQ4（可选）
**Does retrieval-augmented generation outperform direct prompting for UK primary mathematics lesson preparation?**

---

## 6. 文献与政策归纳后的设计结论

### 6.1 课程对齐不是“有题目就行”
英国小学数学强调的不只是会做题，而是：

- fluency
- reasoning
- problem solving
- representations
- mathematical talk
- concepts 之间的连接

因此，系统不应只生成“练习题清单”，而应强制输出：

- 本节核心概念
- 前置知识
- 表征方式
- 提问链
- 易错点
- 评价证据

### 6.2 对低年龄儿童要优先考虑认知负荷
对于 KS1 和 lower KS2，系统生成内容时要特别注意：

- 一次只引入一个主要新点；
- 语言短句化；
- 先具体、再图示、再符号，但允许来回切换；
- 明确给出 sentence stems；
- 通过操作、图示、比较和口头解释支持理解；
- 练习应从高支持到逐步独立；
- 不要让学生在词太多、步骤太多的任务里迷失。

### 6.3 系统应先做“教师端”，不要一开始做“儿童端”
这不是保守，而是更适合毕业设计：

- 教师端更容易评估；
- 风险更可控；
- 不必一开始就处理儿童长期对话、成瘾、情感依赖或错误反馈放大；
- 仍然可以在系统里生成“可给儿童使用的材料”，但默认必须由教师审核。

### 6.4 英国学校语境下必须内置安全与治理
系统至少要有：

- teacher-in-the-loop
- personal data minimisation
- no hidden profiling
- no manipulative or dependency language
- logging and audit trail
- moderation / safeguarding escalation
- child-facing output must be age-appropriate
- teacher review before release

---

## 7. 相关系统与市场对标

英国学校语境下，最值得写入 related work 的不是泛泛而谈“ChatGPT 能写教案”，而是：

### 7.1 Oak National Academy – Aila
Aila 是英国教师向的 AI lesson assistant，能生成 lesson plan、worksheet、quiz、slides，并且明显强调英国课堂语境、RAG 和输出格式控制。  
对你的毕设而言，它最重要的研究意义在于：

- 证明“英国教师备课”是一个真实需求；
- 证明 lesson planning assistant 是可落地方向；
- 说明 curriculum-grounded + format-controlled 的路线是合理的。

### 7.2 其他教师工具
可在 related work 中简述：

- Khanmigo for Educators
- Brisk Teaching
- MagicSchool

但你的重点不应是“谁更火”，而应是：  
**你的系统比通用工具更强调英国课程映射、年龄适配、结构化输出和安全限制。**

---

## 8. 建议系统架构

## 8.1 总体架构（推荐）

### Layer 1: Input Layer
输入参数：

- year group
- topic / unit
- lesson duration
- class profile
- prior learning
- SEND / EAL needs
- desired outputs

### Layer 2: Curriculum & Evidence Retrieval Layer
检索材料建议包括：

- England mathematics programmes of study
- DfE KS1 / KS2 mathematics guidance
- NCETM mastery guidance
- EEF maths guidance
- 你自己整理的 school templates / lesson formats / vocabulary banks

### Layer 3: Planning Engine
大模型根据检索内容和 guardrails 生成：

- lesson objective
- success criteria
- prerequisite knowledge
- misconception analysis
- representations
- teacher questions
- guided practice
- independent practice
- assessment
- differentiation

### Layer 4: Safety & Validation Layer
自动检查：

- 是否是有效 JSON
- 是否使用 British English
- 是否出现 Americanisms
- 是否缺少 curriculum refs
- 是否出现不适合低年龄儿童的长句或多步骤任务
- 是否涉及个人数据
- 是否触发 safeguarding / harmful content

### Layer 5: Human Review & Export Layer
教师审核后导出为：

- lesson plan
- worksheet seed
- exit ticket
- quiz seed
- slide outline

---

## 9. 为什么要用 JSON，而不是直接输出散文式教案

因为你的毕设不仅要“能生成”，还要“可测、可比、可复用、可接系统”。

JSON 的价值在于：

1. **便于做自动评估**：可以检查字段是否缺失。
2. **便于比较模型**：不同模型都按统一结构输出。
3. **便于后续接前端**：网页系统可以直接渲染。
4. **便于导出不同格式**：同一 JSON 可转教案、幻灯片、练习、题卡。
5. **便于论文复现实验**：审阅者更容易理解你的实验设置。

---

## 10. 推荐实验设计

## 10.1 测试数据集怎么做
建议你自己构建一个**小而高质量**的测试集，不要追求海量。

### 推荐规模
**36 个测试任务**

按以下方式均衡采样：

- Year 1–6 各 6 个任务
- 每个年级覆盖 6 类主题：
  - number and place value
  - addition / subtraction / multiplication / division
  - fractions
  - geometry
  - measurement
  - reasoning / problem solving

### 每个任务都固定输入
确保可比性：

- year group
- topic
- duration
- class profile
- prior learning
- support needs
- required output fields

---

## 10.2 系统对比组
建议至少做 3 组：

### Baseline A: Direct Prompting
不给课程检索，只给普通提示词。

### Baseline B: Curriculum-Grounded RAG
加入课程与教学材料检索。

### System C: RAG + Age-Aware Guardrails
在 B 的基础上加入儿童认知和安全限制。

这样论文里就能回答：

- 仅靠模型本身够不够？
- 检索是否提升课程对齐？
- 年龄限制是否提升适配性？

---

## 10.3 评估维度
建议使用 1–5 分量表，由 2–3 名评审人工打分（导师、PGCE 学生、教师志愿者都可以）。

### 维度 1：Curriculum Alignment
- 是否符合对应年级目标？
- 是否匹配英国课程表述？

### 维度 2：Pedagogical Quality
- 目标是否清晰？
- 活动是否可教？
- 是否体现表征、提问、练习和评估？

### 维度 3：Age Appropriateness
- 语言是否过长？
- 任务步骤是否过多？
- 是否考虑低年龄理解方式？

### 维度 4：Misconception Handling
- 是否能识别典型误区？
- 是否给出对应纠正策略？

### 维度 5：Differentiation Quality
- support / core / stretch 是否有实际差异？
- SEND / EAL 是否不是空话？

### 维度 6：Output Reliability
- JSON 是否有效？
- 是否漏字段？
- 是否出现明显幻觉或伪造课程引用？

### 维度 7：Practical Efficiency
- latency
- token usage
- cost per generation

---

## 11. 年龄适配规则（系统必须内置）

这是你毕设里非常重要的一段，最好单独写一节。

## 11.1 Year 1–2
系统输出应：

- 强调 concrete objects、pictures、manipulatives；
- 使用短句；
- 每次一个核心概念；
- 多用 oral rehearsal；
- 给出 sentence stems；
- 任务步骤少；
- 用熟悉情境；
- 预设“数数、对齐、交换顺序、位值混淆”等误区。

## 11.2 Year 3–4
系统输出应：

- 继续保留表征支持；
- 开始增加 reasoning prompts；
- 控制工作记忆负荷；
- 把 word problem 拆小；
- 允许图示、表格和 verbal reasoning 并行。

## 11.3 Year 5–6
系统输出可：

- 增加抽象表达；
- 增加 multi-step problems；
- 让学生比较不同方法；
- 强化 justification；
- 但仍要保证语言清晰、任务结构明确。

---

## 12. 你应该如何限制 AI 模型

对于毕设，最实用的做法不是写一个长 prompt，而是把限制分成“政策层 + 输出层 + 年龄层”。

### 12.1 政策层限制
- 只能面向教师端生成
- 不能跳过教师审核
- 不能请求儿童个人信息
- 不能做心理依赖型对话
- 不能输出不合年龄的内容
- 不得假装自己替代教师专业判断
- 不得虚构课程来源

### 12.2 教学层限制
- 必须包含前置知识、误区、表征、提问、练习、评估
- 必须给出 British English
- 必须尽量避免 Americanisms
- 必须限制每节课的新知识密度
- 必须考虑 SEND / EAL / mixed attainment

### 12.3 输出层限制
- 必须输出 JSON
- 必须满足 schema
- 缺信息时要显式写 assumptions
- 不允许输出额外散文破坏解析
- curriculum refs 必须可追踪

---

## 13. 模型测试建议（论文可操作版本）

你提出“所有 AI 模型”，如果按字面穷举会非常大，也没有必要。  
对毕设来说，最合理的做法是构建一个**覆盖主流闭源、低成本、开源/本地部署和中国模型的代表性测试矩阵**。

### 13.1 核心必测组（建议 8–10 个）
用于论文主实验：

- OpenAI GPT-5.4
- OpenAI GPT-5-mini
- Anthropic Claude Opus 4.6
- Anthropic Claude Sonnet 4.6
- Google Gemini 2.5 Pro
- Google Gemini 2.5 Flash
- DeepSeek Reasoner
- DeepSeek Chat
- Qwen 3.5 Plus
- Qwen 3.5 Flash

### 13.2 扩展对照组（可选）
如果你时间足够，可以加入：

- Anthropic Claude Haiku 4.5
- Google Gemini 2.5 Flash-Lite
- Google Gemini 3.1 Pro Preview
- xAI Grok 4.20 Beta
- Mistral Magistral Medium 1.2
- GLM-5
- Kimi K2.5
- Cohere Command

### 13.3 本地 / 开源部署组（可选）
如果你想讨论学校私有部署或低成本部署：

- OpenAI gpt-oss-20b
- OpenAI gpt-oss-120b
- Qwen 3.5 27B
- Mistral open model（如你实际可部署的版本）

---

## 14. 如何在论文里解释“为什么选这些模型”

你不要写成“我随便挑几个有名的模型”，而要写成：

- **旗舰能力组**：比较高质量 reasoning / long-form planning
- **成本效率组**：比较可落地的低成本批量生成
- **中国模型组**：比较多语种和低成本服务
- **开源/本地组**：比较学校侧私有部署的可能性
- **预览模型组**：探索前沿性能，但单独标记其不稳定性

这样你的模型选择就显得有研究设计，而不是堆名单。

---

## 15. 最推荐的论文主实验组合

如果你时间有限，我最推荐你把主实验缩到 **8 个模型 + 3 个系统配置**。

### 模型（8 个）
- GPT-5.4
- GPT-5-mini
- Claude Opus 4.6
- Claude Sonnet 4.6
- Gemini 2.5 Pro
- Gemini 2.5 Flash
- DeepSeek Reasoner
- Qwen 3.5 Plus

### 配置（3 组）
- direct prompting
- curriculum-grounded RAG
- RAG + age-aware guardrails

这样总实验量是：

**36 tasks × 8 models × 3 settings = 864 generations**

这个规模对英方毕设是偏扎实但仍可管理的。

---

## 16. 伦理与风险控制（论文必须写）

### 16.1 如果只做教师端实验
伦理会容易很多。  
你可以写：

- 本研究不让儿童直接与系统进行独立长对话；
- 生成内容仅供教师审阅与备课参考；
- 不收集儿童可识别个人信息；
- 输出由成年人审核后再进入课堂。

### 16.2 如果你要找教师参与评价
需要说明：

- informed consent
- voluntary participation
- withdrawal rights
- anonymised data storage
- no school-identifiable disclosure
- secure storage and limited retention

### 16.3 如果你想做儿童课堂试用
这会大幅提高伦理门槛。  
除非学校和导师明确支持，否则建议在毕设中先不做真实儿童用户实验，改为：

- 教师评审
- PGCE/ITE 学生评审
- 专家 rubric 评估

---

## 17. 论文结构建议

### Chapter 1 Introduction
- 研究背景
- 问题定义
- 研究目标
- 研究问题
- 贡献

### Chapter 2 Literature Review
- AI in education
- primary mathematics pedagogy
- curriculum-grounded generation
- child cognition and cognitive load
- AI safety, privacy and safeguarding in UK schools

### Chapter 3 System Design
- system architecture
- data sources
- prompt design
- guardrails
- output schema
- validation pipeline

### Chapter 4 Methodology
- task set
- model selection
- experimental conditions
- metrics
- human evaluation design
- ethics

### Chapter 5 Results
- quantitative scores
- qualitative examples
- failure cases
- cost/latency comparison

### Chapter 6 Discussion
- what improved
- what failed
- implications for teachers and schools
- limitations

### Chapter 7 Conclusion
- summary
- contributions
- future work

---

## 18. 你这篇毕设最可能的创新点

你可以把创新写成这四条中的 2–3 条：

1. **英国课程对齐**：不是通用 lesson planner，而是 England primary maths aligned。
2. **低年龄适配约束**：把儿童认知与语言负荷显式写进系统限制。
3. **结构化输出**：以 JSON schema 驱动教案生成、评估和系统落地。
4. **模型比较**：比较不同闭源/开源模型在英国小学数学备课任务上的表现。
5. **安全治理嵌入**：把 safeguarding、privacy、teacher review 作为系统设计的一部分，而不是事后补充。

---

## 19. 你现在最应该先做的 5 件事

1. **锁定研究范围**：先做 teacher-facing，不做 fully autonomous child-facing tutor。
2. **确定课程范围**：先只做 England，不混 Scotland/Wales/NI。
3. **搭建统一 JSON schema**：所有模型都按同一格式输出。
4. **选定主实验模型**：先 8 个核心模型。
5. **建立小而精的测试任务集**：36 个任务足够写出好论文。

---

## 20. 与本报告配套的文件

本报告配套提供以下 JSON 文件：

1. `uk_primary_math_model_guardrails.json`  
   用于约束模型行为、年龄适配、安全和输出规则。

2. `uk_primary_math_lesson_plan_schema.json`  
   用于统一 lesson plan 的 JSON 输出格式。

3. `uk_primary_math_model_test_matrix.json`  
   用于记录建议测试模型、优先级、角色和实验分层。

4. `uk_primary_math_generation_request_example.json`  
   用于给模型发起一次标准化生成请求的示例。

---

## 21. 一句话结论

如果你是做英方毕设，**最稳、最有学术感、也最容易通过的路线**是：

> 做一个“面向英格兰小学数学课程、带年龄适配与安全限制、支持结构化 JSON 输出、并能比较不同模型表现”的 AI 辅助备课系统。

这条路线同时具备：

- 教育价值
- 技术实现价值
- 实验可评估性
- 英国语境合规性
- 毕设可完成性

---

## 22. 参考依据（建议在论文中正式引用的文献/政策）

下面这些是你正文里最值得正式引用的依据来源（请在正式论文中按学校要求转换为 Harvard / APA / IEEE 等格式）：

- Department for Education. *National curriculum in England: mathematics programmes of study.*
- Department for Education. *Mathematics guidance: key stages 1 and 2.*
- National Centre for Excellence in the Teaching of Mathematics (NCETM). *The Five Big Ideas in Teaching for Mastery.*
- Education Endowment Foundation (EEF). *Improving Mathematics in the Early Years and Key Stage 1.*
- Education Endowment Foundation (EEF). *Improving Mathematics in Key Stages 2 and 3.*
- Ofsted. *Mathematics subject report / mathematics research review materials.*
- Department for Education. *Generative AI in education.*
- Department for Education. *Generative AI: product safety expectations.*
- Department for Education. *Keeping Children Safe in Education 2025.*
- Information Commissioner’s Office (ICO). *Children’s code.*
- British Educational Research Association (BERA). *Ethical Guidelines for Educational Research (5th edition).*
- Oak National Academy. *Aila / AI lesson assistant materials.*