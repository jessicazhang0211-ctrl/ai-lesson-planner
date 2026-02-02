const lessonDict = {
  zh: {
    lessonTitle: "教案生成",
    lessonSub: "选择课程信息，填写目标与重点，生成结构化教案。",
    basicInfo: "基本信息",
    grade: "年级",
    subject: "学科",
    topic: "课题",
    duration: "课时",
    teachingDesign: "教学设计",
    objectives: "教学目标",
    keyPoints: "重难点",
    activities: "教学活动",
    generate: "生成教案",
    clear: "清空",
    hint: "小提示：先用“模板生成”，后续接入后端 AI 接口即可一键产出。",
    preview: "预览",
    copy: "复制",
    download: "下载 .txt",
    emptyTitle: "还没有内容",
    emptySub: "填写左侧信息并点击“生成教案”。",
    copied: "已复制到剪贴板",
    required: "请至少填写课题"
  },
  en: {
    lessonTitle: "Lesson Planner",
    lessonSub: "Fill in the lesson context and generate a structured lesson plan.",
    basicInfo: "Basic info",
    grade: "Grade",
    subject: "Subject",
    topic: "Topic",
    duration: "Duration",
    teachingDesign: "Teaching design",
    objectives: "Objectives",
    keyPoints: "Key points & difficulties",
    activities: "Activities",
    generate: "Generate",
    clear: "Clear",
    hint: "Tip: This is a template generator. You can connect your AI API later.",
    preview: "Preview",
    copy: "Copy",
    download: "Download .txt",
    emptyTitle: "No content yet",
    emptySub: "Fill in the form and click “Generate”.",
    copied: "Copied",
    required: "Please fill in at least the topic"
  }
};

function getLocale() {
  return localStorage.getItem("locale") || "zh";
}

function applyLessonLang() {
  const lang = getLocale();
  const t = lessonDict[lang];

  document.querySelectorAll("[data-i18n-page]").forEach(el => {
    const key = el.getAttribute("data-i18n-page");
    if (t[key]) el.textContent = t[key];
  });
}

function val(id) {
  const el = document.getElementById(id);
  return el ? el.value.trim() : "";
}

function templatePlan(input) {
  const lang = getLocale();

  // 简单模板（你后面接 AI：把 input 发给后端即可）
  if (lang === "en") {
    return `Lesson Plan (Template)

1. Basic Info
- Grade: ${input.grade}
- Subject: ${input.subject}
- Topic: ${input.topic}
- Duration: ${input.duration} mins

2. Objectives
${input.objectives || "- (To be completed)"}

3. Key Points & Difficulties
${input.keyPoints || "- (To be completed)"}

4. Teaching Process (Suggested)
${input.activities || `- Warm-up (5 mins)
- Presentation (15 mins)
- Practice (15 mins)
- Summary (3 mins)
- Homework (2 mins)`}

5. Assessment
- Quick check questions
- Exit ticket / short quiz

6. Homework
- Practice task aligned to key points
`;
  }

  return `教案（模板）

一、基本信息
- 年级：${input.grade}
- 学科：${input.subject}
- 课题：${input.topic}
- 课时：${input.duration} 分钟

二、教学目标
${input.objectives || "（待补充：知识/能力/情感目标）"}

三、重难点
${input.keyPoints || "（待补充：重点与难点）"}

四、教学过程（建议）
${input.activities || `1）导入（5分钟）：情境/提问引出主题
2）新授（15分钟）：概念讲解+示例演示
3）练习（15分钟）：分层练习/小组活动
4）总结（3分钟）：回顾要点
5）作业（2分钟）：巩固提升`}

五、评价与反馈
- 课堂提问/随堂练习
- 观察学生参与度与错误点记录

六、作业设计
- 基础题：巩固概念
- 提升题：迁移应用
`;
}

function setOutput(text) {
  const out = document.getElementById("output");
  const empty = document.getElementById("emptyState");
  out.textContent = text || "";
  empty.style.display = text ? "none" : "flex";
}

function downloadTxt(filename, text) {
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function bindLessonEvents() {
  document.getElementById("genBtn").addEventListener("click", (e) => {
    e.preventDefault();

    const input = {
      grade: val("grade"),
      subject: val("subject"),
      topic: val("topic"),
      duration: val("duration"),
      objectives: val("objectives"),
      keyPoints: val("keyPoints"),
      activities: val("activities")
    };

    if (!input.topic) {
      alert(lessonDict[getLocale()].required);
      return;
    }

    const plan = templatePlan(input);
    setOutput(plan);

    // 可选：缓存到本地，刷新不丢
    localStorage.setItem("last_lesson_plan", plan);
  });

  document.getElementById("clearBtn").addEventListener("click", (e) => {
    e.preventDefault();
    ["topic","objectives","keyPoints","activities"].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.value = "";
    });
    setOutput("");
    localStorage.removeItem("last_lesson_plan");
  });

  document.getElementById("copyBtn").addEventListener("click", async (e) => {
    e.preventDefault();
    const text = document.getElementById("output").textContent || "";
    if (!text) return;
    await navigator.clipboard.writeText(text);
    alert(lessonDict[getLocale()].copied);
  });

  document.getElementById("downloadBtn").addEventListener("click", (e) => {
    e.preventDefault();
    const text = document.getElementById("output").textContent || "";
    if (!text) return;

    const name = (val("topic") || "lesson-plan").replace(/[\\/:*?"<>|]/g, "_");
    downloadTxt(`${name}.txt`, text);
  });
}

function initLesson() {
  applyLessonLang();

  const cache = localStorage.getItem("last_lesson_plan");
  if (cache) setOutput(cache);
  else setOutput("");
}

document.addEventListener("DOMContentLoaded", () => {
  initLesson();
  bindLessonEvents();
});
