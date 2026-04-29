const API_BASE = "http://127.0.0.1:5000";

const kbDict = {
  zh: {
    title: "知识库可视化",
    subtitle: "按课题查看历史作业分析的时间线与误区热度。",
    refresh: "刷新",
    importFile: "导入文件",
    importTitle: "导入自定义知识库",
    importSub: "支持 txt/md/json/csv。导入后会在 AI 生成教案与习题前自动注入。",
    tagsLabel: "标签",
    tagsPlaceholder: "例如：计算, 易错点",
    manualContent: "手动录入内容",
    manualContentPlaceholder: "粘贴知识点、方法步骤或常见错因...",
    saveKnowledge: "保存到知识库",
    templateCsv: "下载 CSV 模板",
    templateJson: "下载 JSON 模板",
    templateDownloaded: "模板已下载",
    importOk: "导入成功",
    importFail: "导入失败",
    importRows: "已导入条目",
    customKbTitle: "已导入知识库",
    customKbSub: "这些条目会在 AI 调用前注入到提示词上下文。",
    classLabel: "班级",
    topicLabel: "课题",
    topicSearchPlaceholder: "输入课题关键词搜索",
    recordLabel: "样本数",
    allClass: "全部班级",
    allTopic: "全部课题",
    heatTitle: "误区热度",
    heatSub: "出现次数越高，越应优先纠偏。",
    wrongTitle: "高频错题",
    wrongSub: "按课题聚合的高频错题，用于复习课精准纠偏。",
    timelineTitle: "作业分析时间线",
    timelineSub: "按时间展示该课题下每次批改的学情结论。",
    empty: "暂无数据",
    loadFail: "加载失败",
    completionRate: "完成率",
    score: "得分",
    weakTypes: "薄弱题型",
    misconceptions: "共性误区"
    ,
    wrongQuestions: "错题"
  },
  en: {
    title: "Knowledge Base",
    subtitle: "View assignment-analysis timeline and misconception heat by topic.",
    refresh: "Refresh",
    importFile: "Import File",
    importTitle: "Import Custom Knowledge Base",
    importSub: "Supports txt/md/json/csv. Imported entries are injected before AI generation.",
    tagsLabel: "Tags",
    tagsPlaceholder: "For example: arithmetic, misconception",
    manualContent: "Manual Content",
    manualContentPlaceholder: "Paste knowledge points, methods, or common mistakes...",
    saveKnowledge: "Save to Knowledge Base",
    templateCsv: "Download CSV Template",
    templateJson: "Download JSON Template",
    templateDownloaded: "Template downloaded",
    importOk: "Import succeeded",
    importFail: "Import failed",
    importRows: "Imported rows",
    customKbTitle: "Imported Knowledge",
    customKbSub: "These entries are injected into AI prompts before generation.",
    classLabel: "Class",
    topicLabel: "Topic",
    topicSearchPlaceholder: "Search topic keyword",
    recordLabel: "Records",
    allClass: "All Classes",
    allTopic: "All Topics",
    heatTitle: "Misconception Heat",
    heatSub: "Higher frequency means higher remediation priority.",
    wrongTitle: "Frequent Wrong Questions",
    wrongSub: "Topic-level wrong-question aggregation for precise review remediation.",
    timelineTitle: "Assignment Analysis Timeline",
    timelineSub: "Chronological snapshots of learning insights per topic.",
    empty: "No data",
    loadFail: "Load failed",
    completionRate: "Completion",
    score: "Score",
    weakTypes: "Weak types",
    misconceptions: "Misconceptions"
    ,
    wrongQuestions: "Wrong questions"
  }
};

const i18n = window.I18N || null;
if (i18n) i18n.registerDict("teacherKnowledge", kbDict);

function getLocale() {
  return i18n ? i18n.getLocale() : (localStorage.getItem("locale") || "zh");
}

function t(key) {
  if (i18n) return i18n.t("teacherKnowledge", key, key);
  const lang = getLocale();
  return (kbDict[lang] && kbDict[lang][key]) || kbDict.zh[key] || key;
}

function applyStaticText() {
  document.querySelectorAll("[data-kb-i18n]").forEach((el) => {
    const key = el.getAttribute("data-kb-i18n");
    if (key) el.textContent = t(key);
  });
  const topicSearch = document.getElementById("filterTopicSearch");
  if (topicSearch) topicSearch.placeholder = t("topicSearchPlaceholder");
  const importTags = document.getElementById("importTags");
  if (importTags) importTags.placeholder = t("tagsPlaceholder");
  const importContent = document.getElementById("importContent");
  if (importContent) importContent.placeholder = t("manualContentPlaceholder");
}

function getToken() {
  return localStorage.getItem("auth_token") || "";
}

function getLoginUser() {
  try {
    return JSON.parse(localStorage.getItem("login_user") || "null");
  } catch {
    return null;
  }
}

async function apiGet(path, withUser = false) {
  const token = getToken();
  const headers = { Authorization: `Bearer ${token}` };
  if (withUser) {
    const user = getLoginUser();
    if (user && user.id) headers["X-User-Id"] = String(user.id);
  }
  const res = await fetch(`${API_BASE}${path}`, { headers });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.code !== 0) {
    throw new Error(data.message || "api error");
  }
  return data.data;
}

async function apiPost(path, payload, isForm = false) {
  const token = getToken();
  const headers = { Authorization: `Bearer ${token}` };
  let body = payload;
  if (!isForm) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(payload || {});
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers,
    body,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.code !== 0) {
    throw new Error(data.message || "api error");
  }
  return data.data;
}

let classList = [];
let topicList = [];
let lastData = null;
let lastCustomKnowledge = [];

function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function renderClassOptions() {
  const select = document.getElementById("filterClass");
  if (!select) return;
  const opts = [`<option value="">${t("allClass")}</option>`]
    .concat(classList.map((c) => `<option value="${c.id}">${c.name}</option>`));
  select.innerHTML = opts.join("");
}

function renderTopicOptions(topics, selected) {
  const input = document.getElementById("filterTopicSearch");
  const datalist = document.getElementById("topicDatalist");
  if (!input || !datalist) return;
  topicList = Array.isArray(topics) ? topics : [];
  datalist.innerHTML = topicList
    .map((x) => `<option value="${x.topic}"></option>`)
    .join("");
  input.value = selected || "";
}

function renderHeat(list) {
  const box = document.getElementById("heatList");
  if (!box) return;
  const rows = Array.isArray(list) ? list : [];
  if (!rows.length) {
    box.innerHTML = `<div class="empty-box">${t("empty")}</div>`;
    return;
  }
  const max = Math.max(...rows.map((r) => Number(r.count || 0)), 1);
  box.innerHTML = rows.slice(0, 20).map((row) => {
    const count = Number(row.count || 0);
    const pct = Math.max(4, Math.round((count / max) * 100));
    return `
      <div class="heat-item">
        <div class="heat-top">
          <span class="heat-name" title="${row.name || ""}">${row.name || ""}</span>
          <span class="heat-count">${count}</span>
        </div>
        <div class="heat-bar"><div class="heat-fill" style="width:${pct}%"></div></div>
      </div>
    `;
  }).join("");
}

function renderTimeline(list) {
  const box = document.getElementById("timeline");
  if (!box) return;
  const rows = Array.isArray(list) ? list : [];
  if (!rows.length) {
    box.innerHTML = `<div class="empty-box">${t("empty")}</div>`;
    return;
  }

  box.innerHTML = rows.map((row) => {
    const weak = Array.isArray(row.weak_question_types) ? row.weak_question_types.join(" / ") : "-";
    const mis = Array.isArray(row.common_misconceptions) ? row.common_misconceptions.join(" / ") : "-";
    const scoreText = row.max_score ? `${row.score ?? "-"}/${row.max_score}` : `${row.score ?? "-"}`;
    const wrongQuestions = Array.isArray(row.wrong_questions) ? row.wrong_questions : [];
    const wrongText = wrongQuestions.length
      ? wrongQuestions.map((x) => (x && x.stem) ? x.stem : "").filter(Boolean).slice(0, 2).join(" / ")
      : "-";
    return `
      <div class="timeline-item">
        <div class="timeline-head">
          <div class="timeline-title">${row.topic || row.title || "-"}</div>
          <div class="timeline-time">${row.updated_at || ""}</div>
        </div>
        <div class="timeline-meta">${t("score")}: ${scoreText} · ${t("completionRate")}: ${row.completion_rate ?? "-"}%</div>
        <div class="timeline-meta">${t("weakTypes")}: ${weak || "-"}</div>
        <div class="timeline-meta">${t("misconceptions")}: ${mis || "-"}</div>
        <div class="timeline-meta">${t("wrongQuestions")}: ${wrongText || "-"}</div>
        <div class="timeline-summary">${row.summary || ""}</div>
      </div>
    `;
  }).join("");
}

function renderWrongQuestions(list) {
  const box = document.getElementById("wrongList");
  if (!box) return;
  const rows = Array.isArray(list) ? list : [];
  if (!rows.length) {
    box.innerHTML = `<div class="empty-box">${t("empty")}</div>`;
    return;
  }
  const max = Math.max(...rows.map((r) => Number(r.count || 0)), 1);
  box.innerHTML = rows.slice(0, 12).map((row) => {
    const count = Number(row.count || 0);
    const pct = Math.max(6, Math.round((count / max) * 100));
    const stem = String(row.stem || "");
    const type = String(row.type || "");
    const analysis = String(row.analysis || "");
    return `
      <div class="wrong-item">
        <div class="wrong-top">
          <span class="wrong-type">${type || "-"}</span>
          <span class="wrong-count">${count}</span>
        </div>
        <div class="wrong-stem" title="${stem}">${stem}</div>
        <div class="wrong-bar"><div class="wrong-fill" style="width:${pct}%"></div></div>
        <div class="wrong-analysis">${analysis || ""}</div>
      </div>
    `;
  }).join("");
}

function renderAll(data) {
  lastData = data || {};
  const recordEl = document.getElementById("recordCount");
  if (recordEl) recordEl.textContent = String(lastData.filtered_records || 0);
  renderTopicOptions(lastData.topics || [], lastData.selected_topic || "");
  renderHeat(lastData.misconception_heat || []);
  renderWrongQuestions(lastData.wrong_question_heat || []);
  renderTimeline(lastData.timeline || []);
}

function renderCustomKnowledge(items) {
  const box = document.getElementById("customKbList");
  if (!box) return;
  const rows = Array.isArray(items) ? items : [];
  lastCustomKnowledge = rows;
  if (!rows.length) {
    box.innerHTML = `<div class="empty-box">${t("empty")}</div>`;
    return;
  }

  box.innerHTML = rows.slice(0, 40).map((row) => {
    const topic = escapeHtml(row.topic || "-");
    const title = escapeHtml(row.title || "");
    const content = escapeHtml(row.content || "");
    const tags = Array.isArray(row.tags) ? row.tags.map((x) => escapeHtml(x)).join(" / ") : "";
    const updatedAt = escapeHtml(row.updated_at || "");
    return `
      <div class="custom-kb-item">
        <div class="custom-kb-head">
          <span class="custom-kb-topic" title="${topic}">${topic}</span>
          <span class="custom-kb-time">${updatedAt}</span>
        </div>
        <div class="custom-kb-title">${title || topic}</div>
        <div class="custom-kb-content" title="${content}">${content}</div>
        ${tags ? `<div class="custom-kb-tags"># ${tags}</div>` : ""}
      </div>
    `;
  }).join("");
}

function setImportStatus(message) {
  const box = document.getElementById("importStatus");
  if (!box) return;
  box.textContent = message || "";
}

function downloadTextFile(filename, content, mimeType = "text/plain;charset=utf-8") {
  const blob = new Blob([content || ""], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function downloadTemplate(kind) {
  if (kind === "csv") {
    const csv = [
      "topic,title,content,tags,class_id",
      '分数加减法,同分母分数加法,同分母分数相加时分母不变只加分子,"分数,计算,易错点",',
      '同类项合并,步骤口诀,先看字母及指数是否相同再合并系数,"代数,同类项,方法",'
    ].join("\n");
    downloadTextFile("knowledge_import_template.csv", csv, "text/csv;charset=utf-8");
  } else {
    const payload = {
      items: [
        {
          topic: "分数加减法",
          title: "同分母分数加法",
          content: "同分母分数相加时，分母不变，只把分子相加。",
          tags: ["分数", "计算", "易错点"],
          class_id: null
        },
        {
          topic: "同类项合并",
          title: "步骤口诀",
          content: "先看字母和指数是否相同，相同才能合并，最后保留字母部分。",
          tags: ["代数", "同类项", "方法"],
          class_id: null
        }
      ]
    };
    downloadTextFile(
      "knowledge_import_template.json",
      JSON.stringify(payload, null, 2),
      "application/json;charset=utf-8"
    );
  }
  setImportStatus(t("templateDownloaded"));
}

async function loadCustomKnowledge() {
  const classId = document.getElementById("filterClass")?.value || "";
  const topic = document.getElementById("filterTopicSearch")?.value.trim() || "";
  const params = new URLSearchParams();
  if (classId) params.set("class_id", classId);
  if (topic) params.set("topic", topic);
  params.set("limit", "120");
  try {
    const data = await apiGet(`/api/resource/knowledge-items?${params.toString()}`);
    renderCustomKnowledge(data.items || []);
  } catch {
    renderCustomKnowledge([]);
  }
}

async function importManualKnowledge() {
  const topic = document.getElementById("importTopic")?.value.trim() || "";
  const content = document.getElementById("importContent")?.value.trim() || "";
  const tags = document.getElementById("importTags")?.value.trim() || "";
  const classId = document.getElementById("filterClass")?.value || "";

  if (!topic || !content) {
    setImportStatus(`${t("importFail")}: ${t("topicLabel")} / ${t("manualContent")}`);
    return;
  }

  const btn = document.getElementById("btnImportManual");
  if (btn) btn.disabled = true;
  try {
    const data = await apiPost("/api/resource/knowledge-items/import", {
      topic,
      content,
      tags,
      class_id: classId || undefined,
    });
    setImportStatus(`${t("importOk")} · ${t("importRows")}: ${data.saved || 0}`);
    const contentInput = document.getElementById("importContent");
    if (contentInput) contentInput.value = "";
    await loadCustomKnowledge();
  } catch (e) {
    setImportStatus(`${t("importFail")}: ${(e && e.message) ? e.message : ""}`);
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function importFileKnowledge(file) {
  if (!file) return;
  const topic = document.getElementById("importTopic")?.value.trim() || "";
  const tags = document.getElementById("importTags")?.value.trim() || "";
  const classId = document.getElementById("filterClass")?.value || "";

  const fd = new FormData();
  fd.append("file", file);
  if (topic) fd.append("topic", topic);
  if (tags) fd.append("tags", tags);
  if (classId) fd.append("class_id", classId);

  setImportStatus(`${t("importFile")}...`);
  try {
    const data = await apiPost("/api/resource/knowledge-items/import", fd, true);
    setImportStatus(`${t("importOk")} · ${t("importRows")}: ${data.saved || 0}`);
    await loadCustomKnowledge();
  } catch (e) {
    setImportStatus(`${t("importFail")}: ${(e && e.message) ? e.message : ""}`);
  }
}

async function loadClasses() {
  try {
    const list = await apiGet("/api/class/?status=all", true);
    classList = Array.isArray(list) ? list : [];
  } catch {
    classList = [];
  }
  renderClassOptions();
}

async function loadKnowledge() {
  const classId = document.getElementById("filterClass")?.value || "";
  const topic = document.getElementById("filterTopicSearch")?.value.trim() || "";
  const btn = document.getElementById("btnRefresh");
  if (btn) btn.disabled = true;
  try {
    const params = new URLSearchParams();
    if (classId) params.set("class_id", classId);
    if (topic) params.set("topic", topic);
    params.set("limit", "80");
    const data = await apiGet(`/api/resource/knowledge-base?${params.toString()}`);
    renderAll(data);
    await loadCustomKnowledge();
  } catch (e) {
    const timeline = document.getElementById("timeline");
    const heat = document.getElementById("heatList");
    const wrong = document.getElementById("wrongList");
    const msg = `${t("loadFail")}: ${(e && e.message) ? e.message : ""}`;
    if (timeline) timeline.innerHTML = `<div class="empty-box">${msg}</div>`;
    if (heat) heat.innerHTML = `<div class="empty-box">${msg}</div>`;
    if (wrong) wrong.innerHTML = `<div class="empty-box">${msg}</div>`;
    renderCustomKnowledge([]);
  } finally {
    if (btn) btn.disabled = false;
  }
}

function bindEvents() {
  document.getElementById("btnRefresh")?.addEventListener("click", (e) => {
    e.preventDefault();
    loadKnowledge();
  });
  document.getElementById("filterClass")?.addEventListener("change", () => {
    const topicInput = document.getElementById("filterTopicSearch");
    if (topicInput) topicInput.value = "";
    loadKnowledge();
  });
  document.getElementById("filterTopicSearch")?.addEventListener("change", () => {
    loadKnowledge();
  });
  document.getElementById("filterTopicSearch")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      loadKnowledge();
    }
  });
  document.getElementById("filterTopicSearch")?.addEventListener("input", (e) => {
    const v = String(e.target?.value || "").trim();
    if (!v) {
      loadKnowledge();
    }
  });
  document.getElementById("filterTopicSearch")?.addEventListener("blur", () => {
    loadKnowledge();
  });

  document.getElementById("btnImportManual")?.addEventListener("click", (e) => {
    e.preventDefault();
    importManualKnowledge();
  });

  document.getElementById("kbImportFile")?.addEventListener("change", async (e) => {
    const file = e.target && e.target.files ? e.target.files[0] : null;
    await importFileKnowledge(file);
    if (e.target) e.target.value = "";
  });

  document.getElementById("btnDownloadCsvTemplate")?.addEventListener("click", (e) => {
    e.preventDefault();
    downloadTemplate("csv");
  });

  document.getElementById("btnDownloadJsonTemplate")?.addEventListener("click", (e) => {
    e.preventDefault();
    downloadTemplate("json");
  });
}

window.addEventListener("app:locale-changed", () => {
  applyStaticText();
  if (lastData) renderAll(lastData);
  if (lastCustomKnowledge) renderCustomKnowledge(lastCustomKnowledge);
  renderClassOptions();
});

document.addEventListener("DOMContentLoaded", async () => {
  applyStaticText();
  bindEvents();
  await loadClasses();
  await loadKnowledge();
});
