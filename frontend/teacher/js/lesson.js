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
    required: "Please fill in at least the topic"
  }
};

let pdfFontLoaded = false;
const PDF_FONT_FAMILY = "SanJiZiHaiSongGBK";
const PDF_FONT_FILE_NORMAL = "SanJiZiHaiSongGBK-2.ttf";
const PDF_FONT_FILE_BOLD = "SanJiZiHaiSongGBK-2.ttf";
const PDF_FONT_URL_NORMAL = "../assets/fonts/SanJiZiHaiSongGBK-2.ttf";
const PDF_FONT_URL_BOLD = "../assets/fonts/SanJiZiHaiSongGBK-2.ttf";

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

function getOutputText() {
  const out = document.getElementById("output");
  return out ? (out.textContent || "") : "";
}

const API_BASE = "http://127.0.0.1:5000";

function getToken(){
  return localStorage.getItem('auth_token') || '';
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
      title: meta.topic || "教案",
      meta
    })
  });
  const data = await res.json().catch(()=> ({}));
  if (!res.ok || data.code !== 0) throw new Error(data.message || "save failed");
  return data.data;
}

function showLoading(){
  const out = document.getElementById('output');
  const empty = document.getElementById('emptyState');
  empty.style.display = 'none';
  out.innerHTML = '<div class="spinner"></div><div style="margin-top:8px;color:#9aa3ad">生成中，请稍候...</div>';
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

  const normalBase64 = await loadFontFile(PDF_FONT_URL_NORMAL);
  const boldBase64 = await loadFontFile(PDF_FONT_URL_BOLD);
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
    doc.setFont("helvetica", "normal");
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
      return { level: 3, text: `${h2Match[1]}. ${h2Match[2]}` };
    }

    const h3Match = textLine.match(/^(\d+\.\d+)\s+(.+)$/);
    if (h3Match) {
      return { level: 3, text: `${h3Match[1]} ${h3Match[2]}` };
    }

    const alphaMatch = textLine.match(/^([a-zA-Z])\)\s*(.+)$/);
    if (alphaMatch) {
      return { level: 3, text: `${alphaMatch[1].toUpperCase()}. ${alphaMatch[2]}` };
    }

    const colonMatch = textLine.match(/^([^：:]{1,12})[：:]\s*(.+)?$/);
    if (colonMatch) {
      const label = colonMatch[1];
      const rest = colonMatch[2] ? ` ${colonMatch[2]}` : "";
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

  if (title) {
    const titleLine = `《${title}》教学设计`;
    writeCentered(sizes.title, "bold", titleLine);
  }

  lines.forEach((rawLine) => {
    if (!rawLine.trim()) {
      cursorY += lineHeight(sizes.body) / 2;
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

    const input = {
      grade: val("grade"),
      subject: val("subject"),
      topic: val("topic"),
      duration: val("duration"),
      lesson_count: Number(val("lessonCount") || 1),
      objectives: val("objectives"),
      key_points: val("keyPoints"),
      activities: val("activities"),
      lesson_count: Number(val("lessonCount") || 1)
    };

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
        body: JSON.stringify(input)
      });
      const data = await res.json().catch(()=> ({}));
      if(res.ok && data.code===0){
        setOutput(data.data.lesson_plan);
        localStorage.setItem('last_lesson_plan', data.data.lesson_plan);
        currentLessonId = data.data.lesson_id || null;
        await refreshHistory();
      }else{
        alert('生成失败: ' + (data.message||'未知错误'));
        setOutput('');
      }
    }catch(err){
      alert('网络错误: ' + err.message);
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
    await downloadPdf(`${name}.pdf`, topic || "教案", text, topic);
  });

  document.getElementById("downloadWordBtn").addEventListener("click", (e) => {
    e.preventDefault();
    const text = getOutputText();
    if (!text) return;
    const name = (val("topic") || "lesson-plan").replace(/[\\/:*?"<>|]/g, "_");
    downloadWord(`${name}.doc`, text);
  });
}

function initLesson() {
  applyLessonLang();

  const cache = localStorage.getItem("last_lesson_plan");
  if (cache) setOutput(cache);
  else setOutput("");

  // 初始自动拉取最近生成列表（若已登录且有 token）
  refreshHistory();
}

function renderHistory(list){
  const box = document.getElementById('historyList');
  if(!box) return;
  if(!list || list.length===0){ box.innerHTML='<div style="color:#8a8f98;font-size:12px;">(empty)</div>'; return }
  box.innerHTML = list.map(item=>{
    const topic = item.topic || item.title || '-';
    const lessonCount = item.lesson_count ? `${item.lesson_count}节` : '';
    const meta = [item.grade||'', item.subject||'', item.duration?`${item.duration}分钟`:'', lessonCount].filter(Boolean).join(' · ');
    return `
      <div class="hitem" data-id="${item.id}" data-content="${encodeURIComponent(item.content||'')}">
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
      setOutput(c);
    });
  });
}

async function apiHistory(){
  try{
    const token = getToken();
    if(!token) return [];
    const res = await fetch(`${API_BASE}/api/lesson/history`, { headers: { 'Authorization': `Bearer ${token}` } });
    const data = await res.json().catch(()=>({}));
    if(!res.ok || data.code!==0) return [];
    return data.data;
  }catch{ return [] }
}

async function refreshHistory(){
  const list = await apiHistory();
  renderHistory(list);
}

document.addEventListener("DOMContentLoaded", () => {
  initLesson();
  bindLessonEvents();
  const out = document.getElementById("output");
  if (out) {
    out.addEventListener("input", () => {
      localStorage.setItem("last_lesson_plan", getOutputText());
    });
  }
});
