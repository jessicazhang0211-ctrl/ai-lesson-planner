const lessonDict = {
  zh: {
    lessonTitle: "教案生成",
    lessonSub: "选择课程信息，填写目标与重点，生成结构化教案。",
    basicInfo: "基本信息",
    grade: "年级",
    subject: "学科",
    topic: "课题",
    duration: "课时",
    lessonCount: "节数",
    teachingDesign: "教学设计",
    objectives: "教学目标",
    keyPoints: "重难点",
    activities: "教学活动",
    generate: "生成教案",
    clear: "清空",
    hint: "提示：填写信息后点击“生成教案”，AI 将为您生成完整教案。",
    preview: "预览",
    copy: "复制",
    save: "保存",
    downloadPdf: "下载 PDF",
    downloadWord: "下载 Word",
    emptyTitle: "还没有内容",
    emptySub: "填写左侧信息并点击“生成教案”。",
    copied: "已复制到剪贴板",
    saved: "已保存",
    saveFail: "保存失败",
    required: "请至少填写课题",
    generating: "生成中，请稍候...",
    generateFail: "生成失败",
    unknownError: "未知错误",
    networkError: "网络错误",
    emptyHistory: "(空)",
    lessonUnit: "节",
    minuteUnit: "分钟",
    teacherLabel: "执教者",
    pdfFontError: "PDF 字体加载失败，中文会乱码。请用本地静态服务器打开前端后重试。\n例如：cd frontend && python -m http.server 8000",
    defaultPlanTitle: "教案"
  },
  en: {
    lessonTitle: "Lesson Planner",
    lessonSub: "Fill in the lesson context and generate a structured lesson plan.",
    basicInfo: "Basic info",
    grade: "Grade",
    subject: "Subject",
    topic: "Topic",
    duration: "Duration",
    lessonCount: "Lessons",
    teachingDesign: "Teaching design",
    objectives: "Objectives",
    keyPoints: "Key points & difficulties",
    activities: "Activities",
    generate: "Generate",
    clear: "Clear",
    hint: "Tip: Fill in the details and click 'Generate' to create an AI-powered lesson plan.",
    preview: "Preview",
    copy: "Copy",
    save: "Save",
    downloadPdf: "Download PDF",
    downloadWord: "Download Word",
    emptyTitle: "No content yet",
    emptySub: "Fill in the form and click “Generate”.",
    copied: "Copied",
    saved: "Saved",
    saveFail: "Save failed",
    required: "Please fill in at least the topic",
    generating: "Generating, please wait...",
    generateFail: "Generation failed",
    unknownError: "Unknown error",
    networkError: "Network error",
    emptyHistory: "(empty)",
    lessonUnit: " lessons",
    minuteUnit: " mins",
    teacherLabel: "Teacher",
    pdfFontError: "PDF font loading failed. CJK text may be garbled. Please open frontend via a local HTTP server and try again.\nExample: cd frontend && python -m http.server 8000",
    defaultPlanTitle: "Lesson Plan"
  }
};

let pdfFontLoaded = false;
const PDF_FONT_FAMILY = "SanJiZiHaiSongGBK";
const PDF_FONT_FILE_NORMAL = "SanJiZiHaiSongGBK-2.ttf";
const PDF_FONT_FILE_BOLD = "SanJiZiHaiSongGBK-2.ttf";
const PDF_FONT_URL_NORMAL = "../assets/fonts/SanJiZiHaiSongGBK-2.ttf";
const PDF_FONT_URL_BOLD = "../assets/fonts/SanJiZiHaiSongGBK-2.ttf";

function getFontCandidates(url) {
  const baseName = "SanJiZiHaiSongGBK-2.ttf";
  return [
    url,
    `../assets/fonts/${baseName}`,
    `/assets/fonts/${baseName}`,
    `/frontend/assets/fonts/${baseName}`
  ];
}

function getLocale() {
  return localStorage.getItem("locale") || "zh";
}

function toEnglishGrade(raw) {
  const map = {
    "小学一年级": "Year 1",
    "小学二年级": "Year 2",
    "小学三年级": "Year 3",
    "小学四年级": "Year 4",
    "小学五年级": "Year 5",
    "小学六年级": "Year 6"
  };
  return map[raw] || raw;
}

function toEnglishSubject(raw) {
  const map = {
    "语文": "Chinese",
    "数学": "Math",
    "英语": "English",
    "科学": "Science"
  };
  return map[raw] || raw;
}

function displayGradeForLocale(raw) {
  return getLocale() === "en" ? toEnglishGrade(raw || "") : (raw || "");
}

function displaySubjectForLocale(raw) {
  return getLocale() === "en" ? toEnglishSubject(raw || "") : (raw || "");
}

function normalizeLessonInputForLocale(input) {
  const locale = getLocale();
  if (locale !== "en") return input;
  return {
    ...input,
    grade: toEnglishGrade(input.grade),
    subject: toEnglishSubject(input.subject)
  };
}

function applyLessonLang() {
  const lang = getLocale();
  const t = lessonDict[lang];

  document.querySelectorAll("[data-i18n-page]").forEach(el => {
    const key = el.getAttribute("data-i18n-page");
    if (t[key]) el.textContent = t[key];
  });

  const gradeSel = document.getElementById("grade");
  if (gradeSel) {
    const zhGrades = ["小学一年级", "小学二年级", "小学三年级", "小学四年级", "小学五年级", "小学六年级"];
    const enGrades = ["Year 1", "Year 2", "Year 3", "Year 4", "Year 5", "Year 6"];
    Array.from(gradeSel.options).forEach((opt, idx) => {
      if (idx < zhGrades.length) opt.textContent = lang === "en" ? enGrades[idx] : zhGrades[idx];
    });
  }

  const subjectSel = document.getElementById("subject");
  if (subjectSel) {
    const zhMap = { "语文": "语文", "数学": "数学", "英语": "英语", "科学": "科学" };
    const enMap = { "语文": "Chinese", "数学": "Math", "英语": "English", "科学": "Science" };
    Array.from(subjectSel.options).forEach((opt) => {
      opt.textContent = lang === "en" ? (enMap[opt.value] || opt.value) : (zhMap[opt.value] || opt.value);
    });
  }

  const durationSel = document.getElementById("duration");
  if (durationSel) {
    Array.from(durationSel.options).forEach((opt) => {
      opt.textContent = lang === "en" ? `${opt.value} min` : `${opt.value} 分钟`;
    });
  }

  const topicInput = document.getElementById("topic");
  if (topicInput) topicInput.placeholder = lang === "en" ? "e.g. Introduction to Fractions" : "例如：分数的初步认识";

  const objectivesInput = document.getElementById("objectives");
  if (objectivesInput) objectivesInput.placeholder = lang === "en" ? "Knowledge / skills / affective goals (brief)" : "知识目标/能力目标/情感目标（可简写）";

  const keyPointsInput = document.getElementById("keyPoints");
  if (keyPointsInput) keyPointsInput.placeholder = lang === "en" ? "What are the key points and difficulties?" : "重点、难点分别是什么？";

  const activitiesInput = document.getElementById("activities");
  if (activitiesInput) activitiesInput.placeholder = lang === "en" ? "e.g. Warm-up - Teaching - Practice - Summary - Homework" : "例如：导入—新授—练习—总结—作业";
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
  const raw = text || "";
  out.dataset.rawText = raw;
  renderLatexOutput(raw);
  empty.style.display = text ? "none" : "flex";
}

function escapeHtml(text) {
  return String(text || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function renderLatexOutput(rawText) {
  const out = document.getElementById("output");
  if (!out) return;

  const safe = escapeHtml(rawText).replace(/\n/g, "<br>");
  out.innerHTML = safe;

  if (typeof window.renderMathInElement !== "function") return;
  try {
    window.renderMathInElement(out, {
      delimiters: [
        { left: "$$", right: "$$", display: true },
        { left: "\\[", right: "\\]", display: true },
        { left: "$", right: "$", display: false },
        { left: "\\(", right: "\\)", display: false }
      ],
      throwOnError: false,
      strict: "ignore"
    });
  } catch {
    out.innerHTML = safe;
  }
}

function tryParseJsonObject(raw) {
  if (!raw || typeof raw !== "string") return null;
  const s = raw.trim();
  if (!s.startsWith("{") || !s.endsWith("}")) return null;
  try {
    const obj = JSON.parse(s);
    return (obj && typeof obj === "object" && !Array.isArray(obj)) ? obj : null;
  } catch {
    return null;
  }
}

function formatKvLine(label, value) {
  const v = (value === null || value === undefined) ? "" : String(value).trim();
  return v ? `- ${label}：${v}` : "";
}

function formatLessonJsonToDocText(obj) {
  const locale = getLocale();
  const isEn = locale === "en";
  const lines = [];
  const title = obj.lesson_title || obj.topic || lessonDict[getLocale()].defaultPlanTitle;
  lines.push(String(title));
  lines.push(`${lessonDict[getLocale()].teacherLabel}: ${isEn ? "[Your Name]" : "[您的姓名]"}`);
  lines.push("");

  lines.push(isEn ? "I. Basic Information" : "一、 基本信息");
  [
    formatKvLine(isEn ? "Grade" : "年级", obj.year_group),
    formatKvLine(isEn ? "Subject" : "学科", obj.subject),
    formatKvLine(isEn ? "Topic" : "课题", obj.topic),
    formatKvLine(isEn ? "Subtopic" : "子课题", obj.subtopic),
    formatKvLine(isEn ? "Duration" : "课时", obj.duration_minutes ? `${obj.duration_minutes}${isEn ? " min" : "分钟"}` : ""),
    formatKvLine(isEn ? "Lesson type" : "课程类型", obj.lesson_type),
    formatKvLine(isEn ? "Difficulty" : "难度", obj.difficulty_level)
  ].filter(Boolean).forEach(x => lines.push(x));
  lines.push("");

  lines.push(isEn ? "II. Teaching Objectives" : "二、 教学目标");
  (obj.learning_objectives || []).forEach((x, i) => lines.push(`${i + 1}. ${x}`));
  if (!Array.isArray(obj.learning_objectives) || obj.learning_objectives.length === 0) {
    lines.push(isEn ? "- N/A" : "- 无");
  }
  lines.push("");

  lines.push(isEn ? "III. Key and Difficult Points" : "三、 重难点");
  const misconceptions = Array.isArray(obj.anticipated_misconceptions) ? obj.anticipated_misconceptions : [];
  if (misconceptions.length) {
    lines.push(isEn ? "Common misconceptions and corrections:" : "教学难点与易错点：");
    misconceptions.forEach((m, i) => {
      const issue = (m && m.issue) ? m.issue : "";
      const response = (m && m.response) ? m.response : "";
      if (issue) lines.push(`${i + 1}. ${issue}`);
      if (response) lines.push(`   - ${isEn ? "Correction" : "纠正策略"}: ${response}`);
    });
  } else {
    lines.push(isEn ? "- N/A" : "- 无");
  }
  lines.push("");

  lines.push(isEn ? "IV. Teaching Process" : "四、 教学过程");
  const seq = Array.isArray(obj.teaching_sequence) ? obj.teaching_sequence : [];
  if (seq.length) {
    seq.forEach((step, idx) => {
      const phase = step.phase || (isEn ? `Step ${idx + 1}` : `环节${idx + 1}`);
      const mins = step.duration_minutes ? (isEn ? ` (${step.duration_minutes} min)` : `（${step.duration_minutes}分钟）`) : "";
      lines.push(`${idx + 1}. ${phase}${mins}`);
      if (step.purpose) lines.push(`- ${isEn ? "Purpose" : "目标"}: ${step.purpose}`);
      (step.teacher_actions || []).forEach(x => lines.push(`- ${isEn ? "Teacher action" : "教师活动"}: ${x}`));
      (step.student_activities || []).forEach(x => lines.push(`- ${isEn ? "Student activity" : "学生活动"}: ${x}`));
      (step.assessment_opportunities || []).forEach(x => lines.push(`- ${isEn ? "Assessment" : "评价点"}: ${x}`));
    });
  } else {
    lines.push(isEn ? "- N/A" : "- 无");
  }
  lines.push("");

  lines.push(isEn ? "V. Assessment and Feedback" : "五、 评价与反馈");
  const afl = obj.assessment_for_learning || {};
  [
    formatKvLine(isEn ? "Questioning" : "随堂提问", afl.informal_questioning),
    formatKvLine(isEn ? "Visual checks" : "可视化检查", afl.live_visual_checks),
    formatKvLine(isEn ? "Observation" : "课堂观察", afl.observation),
    formatKvLine(isEn ? "Worksheet evidence" : "练习证据", afl.worksheet_evidence),
    formatKvLine(isEn ? "Spoken reasoning" : "口头表达", afl.spoken_reasoning)
  ].filter(Boolean).forEach(x => lines.push(x));
  if (!Object.keys(afl).length) lines.push(isEn ? "- N/A" : "- 无");
  lines.push("");

  lines.push(isEn ? "VI. Homework Design" : "六、 作业设计");
  const hw = obj.homework || {};
  [
    formatKvLine(isEn ? "Core task" : "基础作业", hw.main_task),
    formatKvLine(isEn ? "Written reflection" : "书面反思", hw.written_reflection),
    formatKvLine(isEn ? "Extension task" : "拓展任务", hw.extension)
  ].filter(Boolean).forEach(x => lines.push(x));
  if (!Object.keys(hw).length) lines.push(isEn ? "- N/A" : "- 无");
  lines.push("");

  lines.push(isEn ? "VII. Teaching Resources" : "七、 教学资源展示");
  const resources = Array.isArray(obj.resources_summary) ? obj.resources_summary : [];
  if (resources.length) {
    lines.push(isEn ? "Classroom resources:" : "课堂资源：");
    resources.forEach((x, i) => lines.push(`${i + 1}. ${x}`));
  }
  const ext = Array.isArray(obj.external_resources) ? obj.external_resources : [];
  if (ext.length) {
    lines.push(isEn ? "External resources:" : "外部资源：");
    ext.forEach((r, i) => {
      const titleText = (r && r.title) ? r.title : (isEn ? `Resource ${i + 1}` : `资源${i + 1}`);
      lines.push(`${i + 1}. ${titleText}`);
      if (r && r.type) lines.push(`   - ${isEn ? "Type" : "类型"}: ${r.type}`);
      if (r && r.url) lines.push(`   - ${isEn ? "URL" : "链接"}: ${r.url}`);
      if (r && r.description) lines.push(`   - ${isEn ? "Description" : "说明"}: ${r.description}`);
      if (r && r.suggested_use) lines.push(`   - ${isEn ? "Suggested use" : "使用建议"}: ${r.suggested_use}`);
    });
  }
  if (!resources.length && !ext.length) lines.push(isEn ? "- N/A" : "- 无");

  return lines.join("\n").trim();
}

function setOutputFromAny(rawText, rawJsonObj) {
  if (rawJsonObj && typeof rawJsonObj === "object") {
    setOutput(formatLessonJsonToDocText(rawJsonObj));
    return;
  }
  const parsed = tryParseJsonObject(rawText);
  if (parsed) {
    setOutput(formatLessonJsonToDocText(parsed));
    return;
  }
  setOutput(rawText || "");
}

function getOutputText() {
  const out = document.getElementById("output");
  return out ? (out.dataset.rawText || out.textContent || "") : "";
}

const API_BASE = "http://127.0.0.1:5000";

function getToken(){
  return localStorage.getItem('auth_token') || '';
}

function isAuthInvalidResponse(res, data) {
  if (!res || res.status !== 401) return false;
  const msg = (data && data.message) ? String(data.message).toLowerCase() : "";
  return msg.includes("invalid or expired token") || msg.includes("missing token");
}

function handleAuthExpired() {
  const locale = getLocale();
  localStorage.removeItem("auth_token");
  localStorage.removeItem("login_user");
  alert(locale === "en" ? "Session expired. Please log in again." : "登录已过期，请重新登录。");
  window.location.href = "../login.html";
}

function getCurrentUserName() {
  const locale = getLocale();
  try {
    const user = JSON.parse(localStorage.getItem("login_user") || "{}");
    return (user.name || user.nickname || user.email || (locale === "en" ? "[Your Name]" : "[您的姓名]")).trim();
  } catch {
    return locale === "en" ? "[Your Name]" : "[您的姓名]";
  }
}

function buildLessonMainTitle(grade, subject, topic) {
  const locale = getLocale();
  const g = (locale === "en" ? toEnglishGrade(grade || "") : (grade || "")).trim();
  const s = (locale === "en" ? toEnglishSubject(subject || "") : (subject || "")).trim();
  const t = (topic || "").trim();
  if (!t) return lessonDict[locale].defaultPlanTitle;
  if (locale === "en") return `${g} ${s} ${t} Lesson Plan`.replace(/\s+/g, " ").trim();
  const topicPart = (t.startsWith("《") && t.endsWith("》")) ? t : `《${t}》`;
  return `${g}${s}${topicPart}教案`;
}

async function apiUpdateLesson(lessonId, content, meta) {
  const token = getToken();
  if (!token) throw new Error("missing token");
  const res = await fetch(`${API_BASE}/api/lesson/${lessonId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`
    },
    body: JSON.stringify({
      content,
      title: meta.topic || lessonDict[getLocale()].defaultPlanTitle,
      meta
    })
  });
  const data = await res.json().catch(()=> ({}));
  if (isAuthInvalidResponse(res, data)) {
    handleAuthExpired();
    throw new Error("auth expired");
  }
  if (!res.ok || data.code !== 0) throw new Error(data.message || "save failed");
  return data.data;
}

function showLoading(){
  const out = document.getElementById('output');
  const empty = document.getElementById('emptyState');
  empty.style.display = 'none';
  delete out.dataset.rawText;
  out.innerHTML = `<div class="spinner"></div><div style="margin-top:8px;color:#9aa3ad">${lessonDict[getLocale()].generating}</div>`;
}

async function ensurePdfFontLoaded(doc) {
  if (pdfFontLoaded) return;
  const loadFontFile = async (url) => {
    const res = await fetch(url);
    if (!res.ok) throw new Error("font load failed");
    const buffer = await res.arrayBuffer();
    const bytes = new Uint8Array(buffer);
    let binary = "";
    for (let i = 0; i < bytes.length; i += 1) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  };

  const loadByCandidates = async (candidates) => {
    let lastError = null;
    for (const u of candidates) {
      try {
        return await loadFontFile(u);
      } catch (e) {
        lastError = e;
      }
    }
    throw lastError || new Error("font load failed");
  };

  const normalBase64 = await loadByCandidates(getFontCandidates(PDF_FONT_URL_NORMAL));
  const boldBase64 = await loadByCandidates(getFontCandidates(PDF_FONT_URL_BOLD));
  doc.addFileToVFS(PDF_FONT_FILE_NORMAL, normalBase64);
  doc.addFileToVFS(PDF_FONT_FILE_BOLD, boldBase64);
  doc.addFont(PDF_FONT_FILE_NORMAL, PDF_FONT_FAMILY, "normal");
  doc.addFont(PDF_FONT_FILE_BOLD, PDF_FONT_FAMILY, "bold");
  pdfFontLoaded = true;
}

async function downloadPdf(filename, title, text, headerText = "") {
  const jspdf = window.jspdf;
  if (!jspdf || !jspdf.jsPDF) return;
  const doc = new jspdf.jsPDF({ unit: "pt", format: "a4" });
  try {
    await ensurePdfFontLoaded(doc);
    doc.setFont(PDF_FONT_FAMILY, "normal");
  } catch {
    alert(lessonDict[getLocale()].pdfFontError);
    return;
  }

  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const marginLeft = 85; // ~3cm
  const marginRight = 71; // ~2.5cm
  const marginTop = 86; // ~3cm include header
  const marginBottom = 86; // ~3cm include footer
  const contentWidth = pageWidth - marginLeft - marginRight;

  const sizes = {
    title: 22,
    h1: 16,
    h2: 14,
    h3: 12,
    body: 12,
    header: 9,
    footer: 9
  };

  const lineHeight = (fontSize) => Math.round(fontSize * 1.5);

  const normalizeText = (raw) => (raw || "")
    .replace(/\*\*/g, "")
    .replace(/^#+\s*/gm, "")
    .replace(/^[-*]\s+/gm, "")
    .replace(/\s+$/gm, "")
    .replace(/^---+$/gm, "")
    .trim();

  const cleaned = normalizeText(text);
  const lines = cleaned.split(/\r?\n/);

  const cnToNum = {
    "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10
  };

  const trimPunctuation = (line) => line.replace(/[。；，：.!?]$/g, "");

  const normalizeHeading = (line) => {
    let textLine = trimPunctuation(line.trim());
    if (!textLine) return { level: 0, text: "" };

    const h1Match = textLine.match(/^([一二三四五六七八九十]+)、\s*(.+)$/);
    if (h1Match) {
      return { level: 1, text: `${h1Match[1]}、 ${h1Match[2]}` };
    }

    const h1Alt = textLine.match(/^第([一二三四五六七八九十]+)课时\s*(.+)?$/);
    if (h1Alt) {
      const rest = h1Alt[2] ? ` ${h1Alt[2]}` : "";
      return { level: 1, text: `第${h1Alt[1]}课时${rest}` };
    }

    if (/教案|教学设计/.test(textLine) && textLine.length <= 20) {
      return { level: 1, text: textLine };
    }

    const parenMatch = textLine.match(/^[（(]([一二三四五六七八九十]+)[)）]\s*(.+)$/);
    if (parenMatch) {
      const num = cnToNum[parenMatch[1]] || "";
      return { level: 3, text: `${num}. ${parenMatch[2]}` };
    }

    const h2Match = textLine.match(/^(\d+)[、.]\s*(.+)$/);
    if (h2Match) {
      return { level: 2, text: `${h2Match[1]}. ${h2Match[2]}` };
    }

    const h3Match = textLine.match(/^(\d+\.\d+)\s+(.+)$/);
    if (h3Match) {
      return { level: 3, text: `${h3Match[1]} ${h3Match[2]}` };
    }

    const alphaMatch = textLine.match(/^([a-zA-Z])\)\s*(.+)$/);
    if (alphaMatch) {
      return { level: 3, text: `${alphaMatch[1].toUpperCase()}. ${alphaMatch[2]}` };
    }

    const colonMatch = textLine.match(/^([^：:]{1,16})[：:]\s*(.+)?$/);
    if (colonMatch) {
      const label = colonMatch[1];
      const rest = colonMatch[2] ? ` ${colonMatch[2]}` : "";
      if (/教学重点|教学难点|重点|难点|易错点|关键问题|教学方法|教学准备|板书设计/.test(label)) {
        return { level: 3, text: `${label}${rest}` };
      }
      return { level: 2, text: `${label}${rest}` };
    }

    const fieldMatch = textLine.match(/^(教学课题|教学目标|教学重点|教学难点|教具|学具准备|学情分析|板书设计|作业设计|课后反思|教学内容)\b/);
    if (fieldMatch) {
      return { level: 2, text: textLine };
    }

    return { level: 0, text: textLine };
  };

  let cursorY = marginTop;

  const addPageBreakIfNeeded = (fontSize) => {
    const lh = lineHeight(fontSize);
    if (cursorY + lh > pageHeight - marginBottom) {
      doc.addPage();
      cursorY = marginTop;
    }
  };

  const writeCentered = (fontSize, fontStyle, textLine) => {
    doc.setFont(doc.getFont().fontName, fontStyle);
    doc.setFontSize(fontSize);
    const width = doc.getTextWidth(textLine);
    const x = Math.max(marginLeft, (pageWidth - width) / 2);
    doc.text(textLine, x, cursorY);
    cursorY += lineHeight(fontSize);
  };

  const writeLeft = (fontSize, fontStyle, textLine, indent = 0) => {
    doc.setFont(doc.getFont().fontName, fontStyle);
    doc.setFontSize(fontSize);
    const lh = lineHeight(fontSize);
    const wrapped = doc.splitTextToSize(textLine, contentWidth - indent);
    wrapped.forEach(part => {
      addPageBreakIfNeeded(fontSize);
      doc.text(part, marginLeft + indent, cursorY);
      cursorY += lh;
    });
  };

  const grade = val("grade");
  const subject = val("subject");
  const topic = val("topic") || title || "";
  const mainTitle = buildLessonMainTitle(grade, subject, topic);
  const teacherName = getCurrentUserName();

  writeCentered(sizes.title, "bold", mainTitle);
  writeCentered(sizes.body, "normal", `${lessonDict[getLocale()].teacherLabel}: ${teacherName}`);
  cursorY += 8;

  const shouldSkipLine = (line) => {
    const cur = (line || "").trim();
    if (!cur) return false;
    if (cur === mainTitle || cur === `《${topic}》教学设计`) return true;
    if (/^(执教者|Teacher)[：:]/i.test(cur)) return true;
    if (/^根据您提供的信息|^这是一份|^以下是|^教学设计好的/.test(cur)) return true;
    return false;
  };

  lines.forEach((rawLine) => {
    if (!rawLine.trim()) {
      cursorY += lineHeight(sizes.body) / 2;
      return;
    }

    if (shouldSkipLine(rawLine)) {
      return;
    }

    const normalized = normalizeHeading(rawLine);
    if (normalized.level === 1) {
      cursorY += 12;
      addPageBreakIfNeeded(sizes.h1);
      writeCentered(sizes.h1, "bold", normalized.text);
      return;
    }

    if (normalized.level === 2) {
      writeLeft(sizes.h2, "bold", normalized.text);
      return;
    }

    if (normalized.level === 3) {
      writeLeft(sizes.h3, "bold", normalized.text);
      return;
    }

    writeLeft(sizes.body, "normal", normalized.text, sizes.body * 2);
  });

  const totalPages = doc.getNumberOfPages();
  for (let i = 1; i <= totalPages; i += 1) {
    doc.setPage(i);
    doc.setFont(doc.getFont().fontName, "normal");
    doc.setFontSize(sizes.header);
    const headerLine = headerText || "";
    const headerWidth = doc.getTextWidth(headerLine);
    doc.text(headerLine, (pageWidth - headerWidth) / 2, 40);

    doc.setFont("times", "normal");
    doc.setFontSize(sizes.footer);
    const pageText = String(i);
    const pageWidthText = doc.getTextWidth(pageText);
    doc.text(pageText, (pageWidth - pageWidthText) / 2, pageHeight - 40);
  }
  doc.save(filename);
}

function downloadWord(filename, text) {
  const escaped = (text || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const html = `<!DOCTYPE html><html><head><meta charset="utf-8"></head><body><pre style="white-space:pre-wrap;font-family:'${PDF_FONT_FAMILY}',sans-serif;">${escaped}</pre></body></html>`;
  const blob = new Blob([html], { type: "application/msword;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
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

let currentLessonId = null;

function bindLessonEvents() {
  document.getElementById("genBtn").addEventListener("click", async (e) => {
    e.preventDefault();

    const input = normalizeLessonInputForLocale({
      grade: val("grade"),
      subject: val("subject"),
      topic: val("topic"),
      duration: val("duration"),
      lesson_count: Number(val("lessonCount") || 1),
      objectives: val("objectives"),
      key_points: val("keyPoints"),
      activities: val("activities"),
      lesson_count: Number(val("lessonCount") || 1)
    });

    if (!input.topic) {
      alert(lessonDict[getLocale()].required);
      return;
    }

    // 发送到后端 AI 生成
    try {
      showLoading();
      const token = getToken();
      if(!token) throw new Error('missing token');
      const res = await fetch(`${API_BASE}/api/lesson/generate`,{
        method: 'POST',
        headers: {
          'Content-Type':'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ ...input, lang: getLocale() })
      });
      const data = await res.json().catch(()=> ({}));
      if (isAuthInvalidResponse(res, data)) {
        handleAuthExpired();
        return;
      }
      if(res.ok && data.code===0){
        setOutputFromAny(data.data.lesson_plan, data.data.lesson_plan_json || null);
        localStorage.setItem('last_lesson_plan', getOutputText());
        currentLessonId = data.data.lesson_id || null;
        await refreshHistory();
      }else{
        const locale = getLocale();
        const detail = locale === "en" ? lessonDict[locale].unknownError : (data.message || lessonDict[locale].unknownError);
        alert(`${lessonDict[locale].generateFail}: ${detail}`);
        setOutput('');
      }
    }catch(err){
      alert(`${lessonDict[getLocale()].networkError}: ${err.message}`);
      setOutput('');
    }
  });

  document.getElementById('refreshHistory')?.addEventListener('click', async (e)=>{
    e.preventDefault();
    await refreshHistory();
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
    const text = getOutputText();
    if (!text) return;
    await navigator.clipboard.writeText(text);
    alert(lessonDict[getLocale()].copied);
  });

  document.getElementById("saveBtn").addEventListener("click", async (e) => {
    e.preventDefault();
    if (!currentLessonId) return;
    const content = getOutputText();
    const meta = {
      topic: val("topic"),
      grade: val("grade"),
      subject: val("subject"),
      duration: val("duration"),
      objectives: val("objectives"),
      key_points: val("keyPoints"),
      activities: val("activities"),
      lesson_count: Number(val("lessonCount") || 1)
    };
    try {
      await apiUpdateLesson(currentLessonId, content, meta);
      localStorage.setItem('last_lesson_plan', content);
      alert(lessonDict[getLocale()].saved);
      await refreshHistory();
    } catch {
      alert(lessonDict[getLocale()].saveFail);
    }
  });

  document.getElementById("downloadPdfBtn").addEventListener("click", async (e) => {
    e.preventDefault();
    const text = getOutputText();
    if (!text) return;
    const name = (val("topic") || "lesson-plan").replace(/[\\/:*?"<>|]/g, "_");
    const topic = val("topic") || "";
    await downloadPdf(`${name}.pdf`, topic || lessonDict[getLocale()].defaultPlanTitle, text, topic);
  });

}

function initLesson() {
  applyLessonLang();

  // 历史为空时不回退本地缓存，避免显示过期内容。
  setOutput("");

  // 初始自动拉取最近生成列表，并默认展示最近一条
  refreshHistory({ autoOpenLatest: true });
}

function renderHistory(list){
  const box = document.getElementById('historyList');
  if(!box) return;
  if(!list || list.length===0){ box.innerHTML=`<div style="color:#8a8f98;font-size:12px;">${lessonDict[getLocale()].emptyHistory}</div>`; return }
  box.innerHTML = list.map(item=>{
    const topic = item.topic || item.title || '-';
    const lessonCount = item.lesson_count ? `${item.lesson_count}${lessonDict[getLocale()].lessonUnit}` : '';
    const meta = [displayGradeForLocale(item.grade), displaySubjectForLocale(item.subject), item.duration?`${item.duration}${lessonDict[getLocale()].minuteUnit}`:'', lessonCount].filter(Boolean).join(' · ');
    const active = currentLessonId === Number(item.id) ? 'active' : '';
    return `
      <div class="hitem ${active}" data-id="${item.id}" data-content="${encodeURIComponent(item.content||'')}">
        <div class="hitem-top">
          <div class="hitem-title">${topic}</div>
          <div class="hitem-meta">${(item.created_at||'').slice(0,19).replace('T',' ')}</div>
        </div>
        <div class="hitem-sub">${meta}</div>
      </div>
    `;
  }).join('');
  box.querySelectorAll('.hitem').forEach(el=>{
    el.addEventListener('click', ()=>{
      const c = decodeURIComponent(el.getAttribute('data-content')||'');
      currentLessonId = Number(el.getAttribute('data-id')) || null;
      setOutputFromAny(c, null);
      localStorage.setItem('last_lesson_plan', getOutputText());
      renderHistory(list);
    });
  });
}

async function apiHistory(){
  try{
    const token = getToken();
    if(!token) return [];
    const res = await fetch(`${API_BASE}/api/lesson/history`, { headers: { 'Authorization': `Bearer ${token}` } });
    const data = await res.json().catch(()=>({}));
    if (isAuthInvalidResponse(res, data)) {
      handleAuthExpired();
      return [];
    }
    if(!res.ok || data.code!==0) return [];
    return data.data;
  }catch{ return [] }
}

async function refreshHistory(options = {}){
  const autoOpenLatest = Boolean(options.autoOpenLatest);
  const list = await apiHistory();
  if (autoOpenLatest) {
    if (Array.isArray(list) && list.length > 0) {
      const latest = list[0];
      currentLessonId = Number(latest.id) || null;
      setOutputFromAny(latest.content || "", null);
      localStorage.setItem('last_lesson_plan', getOutputText());
    } else {
      currentLessonId = null;
      setOutput("");
      localStorage.removeItem('last_lesson_plan');
    }
  }
  renderHistory(list);
}

document.addEventListener("DOMContentLoaded", () => {
  initLesson();
  bindLessonEvents();
  const out = document.getElementById("output");
  if (out) {
    out.addEventListener("input", () => {
      out.dataset.rawText = out.innerText || "";
      localStorage.setItem("last_lesson_plan", getOutputText());
    });
  }
});
