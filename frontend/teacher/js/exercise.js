const exerciseDict = {
  zh: {
    title:"习题设计", sub:"选择题型与难度，生成可直接发给学生的练习题。",
    config:"配置", grade:"年级", subject:"学科", topic:"知识点/主题",
    types:"题型", tSingle:"单选", tFill:"填空", tShort:"简答",
    difficulty:"难度", easy:"简单", medium:"中等", hard:"较难",
    count:"题量", includeAnswer:"包含答案解析", yes:"是", no:"否",
    generate:"生成习题", clear:"清空", hint:"目前为模板生成 + 数据库存档，后续可接入 AI 模型提升题目质量。",
    preview:"预览", copy:"复制", download:"下载 .txt",
    emptyTitle:"还没有内容", emptySub:"填写左侧信息并点击“生成习题”。",
    required:"请至少填写知识点/主题", copied:"已复制到剪贴板",
    history:"最近生成", refresh:"刷新", loading:"生成中...", loadFail:"加载失败",
    genFail:"生成失败：请检查后端是否启动 / 路由是否注册 / login_user 是否包含 id"
  },
  en: {
    title:"Exercise Builder", sub:"Choose types & difficulty and generate ready-to-use exercises.",
    config:"Config", grade:"Grade", subject:"Subject", topic:"Topic/Skill",
    types:"Types", tSingle:"Single choice", tFill:"Fill in", tShort:"Short answer",
    difficulty:"Difficulty", easy:"Easy", medium:"Medium", hard:"Hard",
    count:"Count", includeAnswer:"Include answers", yes:"Yes", no:"No",
    generate:"Generate", clear:"Clear", hint:"Template generator + saved to DB. You can plug in AI later.",
    preview:"Preview", copy:"Copy", download:"Download .txt",
    emptyTitle:"No content yet", emptySub:"Fill the form and click “Generate”.",
    required:"Please fill in the topic/skill", copied:"Copied",
    history:"Recent", refresh:"Refresh", loading:"Generating...", loadFail:"Load failed",
    genFail:"Failed: check backend / route registration / login_user has id"
  }
};

const API_BASE = "http://127.0.0.1:5000";

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

async function apiGenerate(payload){
  const userId = getUserId();
  if (!userId) throw new Error("missing user id");

  const res = await fetch(`${API_BASE}/api/exercise/generate`,{
    method:"POST",
    headers:{
      "Content-Type":"application/json",
      "X-User-Id": userId
    },
    body: JSON.stringify(payload)
  });
  const data = await res.json().catch(()=> ({}));
  if(!res.ok || data.code !== 0) throw new Error(data.message || "generate failed");
  return data.data; // {set_id, content}
}

async function apiHistory(){
  const userId = getUserId();
  if (!userId) throw new Error("missing user id");

  const res = await fetch(`${API_BASE}/api/exercise/history`,{
    headers:{
      "X-User-Id": userId
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
      setOutput(content);
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
      setOutput(r.content);
      localStorage.setItem("last_exercise", r.content);
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
    const text = document.getElementById("output").textContent || "";
    if(!text) return;
    await navigator.clipboard.writeText(text);
    alert(t("copied"));
  });

  document.getElementById("downloadBtn").addEventListener("click",(e)=>{
    e.preventDefault();
    const text = document.getElementById("output").textContent || "";
    if(!text) return;
    const name = (val("topic") || "exercises").replace(/[\\/:*?"<>|]/g, "_");
    downloadTxt(`${name}.txt`, text);
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
});
