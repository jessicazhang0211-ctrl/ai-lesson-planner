const exerciseDict = {
  zh: {
    title:"习题设计", sub:"选择题型与难度，生成可直接发给学生的练习题。",
    config:"配置", grade:"年级", subject:"学科", topic:"知识点/主题",
    types:"题型", tSingle:"单选", tFill:"填空", tShort:"简答",
    difficulty:"难度", easy:"简单", medium:"中等", hard:"较难",
    count:"题量", includeAnswer:"包含答案解析", yes:"是", no:"否",
    generate:"生成习题", clear:"清空", hint:"目前为模板生成 + 数据库存档，后续可接入 AI 模型提升题目质量。",
    preview:"预览", copy:"复制", save:"保存", downloadPdf:"下载 PDF", downloadWord:"下载 Word",
    emptyTitle:"还没有内容", emptySub:"填写左侧信息并点击“生成习题”。",
    required:"请至少填写知识点/主题", copied:"已复制到剪贴板",
    history:"最近生成", refresh:"刷新", loading:"生成中...", loadFail:"加载失败", saved:"已保存", saveFail:"保存失败",
    genFail:"生成失败：请检查后端是否启动 / 路由是否注册 / login_user 是否包含 id"
  },
  en: {
    title:"Exercise Builder", sub:"Choose types & difficulty and generate ready-to-use exercises.",
    config:"Config", grade:"Grade", subject:"Subject", topic:"Topic/Skill",
    types:"Types", tSingle:"Single choice", tFill:"Fill in", tShort:"Short answer",
    difficulty:"Difficulty", easy:"Easy", medium:"Medium", hard:"Hard",
    count:"Count", includeAnswer:"Include answers", yes:"Yes", no:"No",
    generate:"Generate", clear:"Clear", hint:"Template generator + saved to DB. You can plug in AI later.",
    preview:"Preview", copy:"Copy", save:"Save", downloadPdf:"Download PDF", downloadWord:"Download Word",
    emptyTitle:"No content yet", emptySub:"Fill the form and click “Generate”.",
    required:"Please fill in the topic/skill", copied:"Copied",
    history:"Recent", refresh:"Refresh", loading:"Generating...", loadFail:"Load failed", saved:"Saved", saveFail:"Save failed",
    genFail:"Failed: check backend / route registration / login_user has id"
  }
};

let pdfFontLoaded = false;
const PDF_FONT_FAMILY = "SanJiZiHaiSongGBK";
const PDF_FONT_FILE_NORMAL = "SanJiZiHaiSongGBK-2.ttf";
const PDF_FONT_FILE_BOLD = "SanJiZiHaiSongGBK-2.ttf";
const PDF_FONT_URL_NORMAL = "../assets/fonts/SanJiZiHaiSongGBK-2.ttf";
const PDF_FONT_URL_BOLD = "../assets/fonts/SanJiZiHaiSongGBK-2.ttf";

const API_BASE = "http://127.0.0.1:5000";

function getToken(){
  return localStorage.getItem('auth_token') || '';
}

function getLocale(){ return localStorage.getItem("locale") || "zh"; }
function t(k){ return exerciseDict[getLocale()][k] || k; }

function applyExerciseLang(){
  document.querySelectorAll("[data-i18n-page]").forEach(el=>{
    const key = el.getAttribute("data-i18n-page");
    if (exerciseDict[getLocale()][key]) el.textContent = exerciseDict[getLocale()][key];
  });
}

function getUserId(){
  try{
    const u = JSON.parse(localStorage.getItem("login_user") || "{}");
    return u.id || u.user_id || "";
  }catch{ return ""; }
}

function val(id){
  const el = document.getElementById(id);
  return el ? el.value.trim() : "";
}

function checkedTypes(){
  return Array.from(document.querySelectorAll(".chip input[type='checkbox']:checked"))
    .map(x=>x.value);
}

function setOutput(text){
  const out = document.getElementById("output");
  const empty = document.getElementById("emptyState");
  out.textContent = text || "";
  empty.style.display = text ? "none" : "flex";
}

function getOutputText(){
  const out = document.getElementById("output");
  return out ? (out.textContent || "") : "";
}

function tryParseJson(raw){
  if (!raw) return null;
  const cleaned = raw.trim();
  if (!cleaned) return null;
  let text = cleaned;
  if (text.startsWith("```")) {
    text = text.replace("```json", "").replace("```", "").trim();
  }
  try { return JSON.parse(text); } catch {}
  const start = text.indexOf("{");
  const end = text.lastIndexOf("}");
  if (start !== -1 && end !== -1 && end > start) {
    try { return JSON.parse(text.slice(start, end + 1)); } catch {}
  }
  return null;
}

function formatExerciseContent(raw, meta){
  const data = tryParseJson(raw);
  if (!data) return raw || "";
  const lines = [];
  const title = data.title || (meta && meta.topic) || "";
  if (title) lines.push(title);
  const info = [data.grade || meta?.grade, data.subject || meta?.subject, data.topic || meta?.topic]
    .filter(Boolean).join(" · ");
  if (info) lines.push(info);
  if (lines.length) lines.push("");

  const includeAnswer = (meta && meta.includeAnswer) || "yes";
  (data.questions || []).forEach((q, idx) => {
    const no = idx + 1;
    lines.push(`${no}. ${q.stem || ""}`.trim());
    if (Array.isArray(q.options) && q.options.length) {
      q.options.forEach((opt, optIdx) => {
        const letter = String.fromCharCode(65 + optIdx);
        lines.push(`   ${letter}. ${opt}`);
      });
    }
    if (includeAnswer === "yes") {
      if (q.answer !== undefined) {
        const ans = Array.isArray(q.answer) ? q.answer.join(", ") : String(q.answer);
        lines.push(`   答案：${ans}`);
      }
      if (q.analysis) lines.push(`   解析：${q.analysis}`);
    }
    if (q.score) lines.push(`   分值：${q.score}`);
    lines.push("");
  });
  return lines.join("\n").trim();
}

function downloadTxt(filename, text){
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

async function downloadPdf(filename, title, text) {
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
  const marginX = 40;
  const marginTop = 48;
  const lineHeight = 16;

  if (title) {
    doc.setFont(doc.getFont().fontName, "bold");
    doc.setFontSize(16);
    doc.text(title, marginX, marginTop);
  }

  doc.setFont(doc.getFont().fontName, "normal");
  doc.setFontSize(11);
  const textLines = doc.splitTextToSize(text || "", pageWidth - marginX * 2);
  let cursorY = marginTop + (title ? 24 : 0);
  textLines.forEach(line => {
    if (cursorY + lineHeight > pageHeight - marginTop) {
      doc.addPage();
      cursorY = marginTop;
    }
    doc.text(line, marginX, cursorY);
    cursorY += lineHeight;
  });
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

async function apiGenerate(payload){
  const token = getToken();
  if (!token) throw new Error("missing token");

  const res = await fetch(`${API_BASE}/api/exercise/generate`,{
    method:"POST",
    headers:{
      "Content-Type":"application/json",
      "Authorization": `Bearer ${token}`
    },
    body: JSON.stringify(payload)
  });
  const data = await res.json().catch(()=> ({}));
  if(!res.ok || data.code !== 0) throw new Error(data.message || "generate failed");
  return data.data; // {set_id, content, exercise_id}
}

async function apiUpdateExercise(exerciseId, content, meta){
  const token = getToken();
  if (!token) throw new Error("missing token");
  const res = await fetch(`${API_BASE}/api/exercise/${exerciseId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`
    },
    body: JSON.stringify({
      content,
      title: meta.topic || "习题",
      meta
    })
  });
  const data = await res.json().catch(()=> ({}));
  if (!res.ok || data.code !== 0) throw new Error(data.message || "save failed");
  return data.data;
}

async function apiHistory(){
  const token = getToken();
  if (!token) throw new Error("missing token");

  const res = await fetch(`${API_BASE}/api/exercise/history`,{
    headers:{
      "Authorization": `Bearer ${token}`
    }
  });
  const data = await res.json().catch(()=> ({}));
  if(!res.ok || data.code !== 0) throw new Error(data.message || "history failed");
  return data.data; // list
}

function renderHistory(list){
  const box = document.getElementById("historyList");
  if(!box) return;
  if(!list || list.length===0){
    box.innerHTML = `<div style="color:#8a8f98;font-size:12px;">(empty)</div>`;
    return;
  }
  box.innerHTML = list.map(item=>{
    // 兼容老数据
    const types = item.types ? (Array.isArray(item.types) ? item.types.join(',') : item.types) : '';
    const difficulty = item.difficulty || '';
    const count = item.count || '';
    const includeAnswer = item.includeAnswer ? (item.includeAnswer==='yes'?'含解析':'无解析') : '';
    const grade = item.grade || '';
    const subject = item.subject || '';
    const topic = item.topic || item.title || '-';
    const sub = [grade, subject, types, difficulty, count?`题量${count}`:'', includeAnswer].filter(Boolean).join(' · ');
    return `
    <div class="hitem" data-id="${item.id}" data-content="${encodeURIComponent(item.content||item.description||'')}">
      <div class="hitem-top">
        <div class="hitem-title">${topic}</div>
        <div class="hitem-meta">${(item.created_at||"").slice(0,19).replace("T"," ")}</div>
      </div>
      <div class="hitem-sub">${sub}</div>
    </div>
    `;
  }).join("");

  // 点击加载详情，预览区显示内容
  box.querySelectorAll(".hitem").forEach(el=>{
    el.addEventListener("click", ()=>{
      const content = decodeURIComponent(el.getAttribute("data-content") || "");
      const id = Number(el.getAttribute("data-id")) || null;
      currentExerciseId = id;
      const item = list.find(i => Number(i.id) === id) || {};
      setOutput(formatExerciseContent(content, item));
    });
  });
}

function payloadFromForm(){
  return {
    lang: getLocale(),
    grade: val("grade"),
    subject: val("subject"),
    topic: val("topic"),
    difficulty: val("difficulty"),
    count: Number(val("count") || 10),
    types: checkedTypes(),
    includeAnswer: val("includeAnswer")
  };
}

let currentExerciseId = null;

function bindEvents(){
  document.getElementById("genBtn").addEventListener("click", async (e)=>{
    e.preventDefault();
    const p = payloadFromForm();
    if(!p.topic){
      alert(t("required"));
      return;
    }
    setOutput(t("loading"));
    try{
      const r = await apiGenerate(p);
      const formatted = formatExerciseContent(r.content, p);
      setOutput(formatted);
      localStorage.setItem("last_exercise", formatted);
      currentExerciseId = r.exercise_id || null;
      await refreshHistory();
    }catch(err){
      console.error(err);
      alert(t("genFail"));
      setOutput("");
    }
  });

  document.getElementById("clearBtn").addEventListener("click",(e)=>{
    e.preventDefault();
    document.getElementById("topic").value = "";
    setOutput("");
    localStorage.removeItem("last_exercise");
  });

  document.getElementById("copyBtn").addEventListener("click", async (e)=>{
    e.preventDefault();
    const text = getOutputText();
    if(!text) return;
    await navigator.clipboard.writeText(text);
    alert(t("copied"));
  });

  document.getElementById("saveBtn").addEventListener("click", async (e)=>{
    e.preventDefault();
    if (!currentExerciseId) return;
    const text = getOutputText();
    const meta = payloadFromForm();
    try{
      await apiUpdateExercise(currentExerciseId, text, meta);
      localStorage.setItem("last_exercise", text);
      alert(t("saved"));
      await refreshHistory();
    }catch(err){
      console.error(err);
      alert(t("saveFail"));
    }
  });

  document.getElementById("downloadPdfBtn").addEventListener("click", async (e)=>{
    e.preventDefault();
    const text = getOutputText();
    if(!text) return;
    const name = (val("topic") || "exercises").replace(/[\\/:*?"<>|]/g, "_");
    await downloadPdf(`${name}.pdf`, val("topic") || "习题", text);
  });

  document.getElementById("downloadWordBtn").addEventListener("click", (e)=>{
    e.preventDefault();
    const text = getOutputText();
    if(!text) return;
    const name = (val("topic") || "exercises").replace(/[\\/:*?"<>|]/g, "_");
    downloadWord(`${name}.doc`, text);
  });

  document.getElementById("refreshHistory").addEventListener("click", async (e)=>{
    e.preventDefault();
    await refreshHistory();
  });
}

async function refreshHistory(){
  try{
    const list = await apiHistory();
    renderHistory(list);
  }catch(err){
    console.error(err);
    renderHistory([]);
  }
}

document.addEventListener("DOMContentLoaded", async ()=>{
  applyExerciseLang();

  const cache = localStorage.getItem("last_exercise");
  if(cache) setOutput(cache); else setOutput("");

  bindEvents();
  await refreshHistory();

  const out = document.getElementById("output");
  if (out) {
    out.addEventListener("input", () => {
      localStorage.setItem("last_exercise", getOutputText());
    });
  }
});
