const API_BASE = "http://127.0.0.1:5000";

const valDict = {
  zh: {
    title: "验证日志",
    subtitle: "查看 JSON 解析、自动校验和人工复核触发原因。",
    refresh: "刷新",
    entityType: "对象类型",
    reviewType: "状态",
    limit: "数量",
    all: "全部",
    thTime: "时间",
    thEntity: "对象",
    thStep: "步骤",
    thParse: "解析",
    thValidation: "校验",
    thNeedReview: "复核",
    thReasons: "原因",
    thAction: "操作",
    empty: "暂无数据",
    yes: "是",
    no: "否",
    loadFail: "加载失败",
    statTotal: "总记录",
    statNeedReview: "待复核",
    statPassed: "已通过",
    statParseIssues: "解析异常",
    keyword: "关键词",
    keywordPlaceholder: "搜索对象、状态或原因",
    handle: "去处理",
    unavailable: "不可用"
  },
  en: {
    title: "Validation Logs",
    subtitle: "Track JSON parsing, auto-validation, and review-trigger reasons.",
    refresh: "Refresh",
    entityType: "Entity Type",
    reviewType: "Status",
    limit: "Limit",
    all: "All",
    thTime: "Time",
    thEntity: "Entity",
    thStep: "Step",
    thParse: "Parse",
    thValidation: "Validation",
    thNeedReview: "Need Review",
    thReasons: "Reasons",
    thAction: "Action",
    empty: "No data",
    yes: "Yes",
    no: "No",
    loadFail: "Load failed",
    statTotal: "Total",
    statNeedReview: "Need Review",
    statPassed: "Passed",
    statParseIssues: "Parse Issues",
    keyword: "Keyword",
    keywordPlaceholder: "Search entity, status, or reason",
    handle: "Open",
    unavailable: "N/A"
  }
};

const i18n = window.I18N || null;
if (i18n) i18n.registerDict("teacherValidation", valDict);

function getLocale() {
  return i18n ? i18n.getLocale() : (localStorage.getItem("locale") || "zh");
}

function t(key) {
  if (i18n) return i18n.t("teacherValidation", key, key);
  const lang = getLocale();
  return (valDict[lang] && valDict[lang][key]) || valDict.zh[key] || key;
}

function applyText() {
  document.querySelectorAll("[data-v-i18n]").forEach((el) => {
    const key = el.getAttribute("data-v-i18n");
    if (key) el.textContent = t(key);
  });
  document.querySelectorAll("[data-v-placeholder]").forEach((el) => {
    const key = el.getAttribute("data-v-placeholder");
    if (key) el.setAttribute("placeholder", t(key));
  });
}

function getToken() {
  return localStorage.getItem("auth_token") || "";
}

async function apiGet(path) {
  const token = getToken();
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.code !== 0) {
    throw new Error(data.message || "api error");
  }
  return data.data;
}

let rawRows = [];
let visibleRows = [];

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function formatReasons(row) {
  const list = Array.isArray(row.reasons) ? row.reasons.filter(Boolean) : [];
  if (list.length) return list.join(" | ");
  return row.review_reason || "";
}

function badge(text, className) {
  const label = escapeHtml(text || "unknown");
  return `<span class="badge ${className}">${label}</span>`;
}

function statusBadge(value, type) {
  const raw = String(value || "unknown");
  const normalized = raw.toLowerCase();
  if (normalized === "passed" || normalized === "ok" || normalized === "success") {
    return badge(raw, "badge-ok");
  }
  if (normalized === "need_review" || normalized === "review") {
    return badge(raw, "badge-review");
  }
  if (normalized.includes("fail") || normalized.includes("error") || normalized.includes("invalid")) {
    return badge(raw, "badge-danger");
  }
  if (type === "parse" && normalized !== "unknown" && normalized !== "not_required") {
    return badge(raw, "badge-ok");
  }
  return badge(raw, "badge-muted");
}

function actionUrl(row) {
  const id = Number(row && row.entity_id);
  if (!id) return "";
  const type = String(row.entity_type || "").toLowerCase();
  if (type === "lesson") {
    return `./lesson.html?lesson_id=${encodeURIComponent(id)}&from=validation`;
  }
  if (type === "exercise") {
    return `./exercise.html?exercise_id=${encodeURIComponent(id)}&from=validation`;
  }
  return "";
}

function actionCell(row) {
  const url = actionUrl(row);
  if (!url) return `<span class="action-unavailable">${t("unavailable")}</span>`;
  return `<a class="action-link" href="${escapeHtml(url)}">${t("handle")}</a>`;
}

function updateStats(rows) {
  const list = Array.isArray(rows) ? rows : [];
  const total = list.length;
  const needReview = list.filter((x) => !!x.need_review).length;
  const passed = list.filter((x) => !x.need_review && String(x.validation_status || "").toLowerCase() === "passed").length;
  const parseIssues = list.filter((x) => {
    const s = String(x.parse_status || "").toLowerCase();
    return s.includes("fail") || s.includes("error") || s.includes("invalid") || s === "unknown";
  }).length;

  const statTotal = document.getElementById("statTotal");
  const statNeedReview = document.getElementById("statNeedReview");
  const statPassed = document.getElementById("statPassed");
  const statParseIssues = document.getElementById("statParseIssues");
  if (statTotal) statTotal.textContent = String(total);
  if (statNeedReview) statNeedReview.textContent = String(needReview);
  if (statPassed) statPassed.textContent = String(passed);
  if (statParseIssues) statParseIssues.textContent = String(parseIssues);
}

function render(rows) {
  visibleRows = Array.isArray(rows) ? rows : [];
  const tbody = document.getElementById("tableBody");
  const empty = document.getElementById("emptyBox");
  if (!tbody || !empty) return;

  if (!visibleRows.length) {
    tbody.innerHTML = "";
    empty.style.display = "block";
    empty.textContent = t("empty");
    return;
  }

  empty.style.display = "none";
  tbody.innerHTML = visibleRows.map((row) => {
    const reviewBadge = row.need_review
      ? `<span class="badge badge-review">${t("yes")}</span>`
      : `<span class="badge badge-ok">${t("no")}</span>`;
    const entity = `${row.entity_type || ""}#${row.entity_id || ""}`;
    const reasons = formatReasons(row);

    return `
      <tr>
        <td>${escapeHtml(row.created_at || "")}</td>
        <td><span class="entity-pill" title="${escapeHtml(entity)}">${escapeHtml(entity)}</span></td>
        <td class="step-cell">${escapeHtml(row.step_no || "-")}</td>
        <td>${statusBadge(row.parse_status, "parse")}</td>
        <td>${statusBadge(row.validation_status, "validation")}</td>
        <td>${reviewBadge}</td>
        <td class="cell-reasons"><div class="reason-list" title="${escapeHtml(reasons)}">${escapeHtml(reasons || "-")}</div></td>
        <td>${actionCell(row)}</td>
      </tr>
    `;
  }).join("");
}

function applyClientFilter(rows) {
  const review = document.getElementById("filterReview")?.value || "";
  const keyword = (document.getElementById("filterKeyword")?.value || "").trim().toLowerCase();
  let result = Array.isArray(rows) ? rows : [];
  if (review === "need_review") result = result.filter((x) => !!x.need_review);
  if (review === "passed") result = result.filter((x) => !x.need_review);
  if (keyword) {
    result = result.filter((row) => {
      const text = [
        row.created_at,
        row.entity_type,
        row.entity_id,
        row.step_no,
        row.parse_status,
        row.validation_status,
        formatReasons(row)
      ].join(" ").toLowerCase();
      return text.includes(keyword);
    });
  }
  return result;
}

function applyFiltersAndRender() {
  render(applyClientFilter(rawRows));
}

async function loadLogs() {
  const entityType = document.getElementById("filterEntityType")?.value || "";
  const limit = document.getElementById("filterLimit")?.value || "100";
  const btn = document.getElementById("btnRefresh");
  if (btn) btn.disabled = true;
  try {
    const params = new URLSearchParams();
    if (entityType) params.set("entity_type", entityType);
    params.set("limit", limit);
    const rows = await apiGet(`/api/lesson/validation-logs?${params.toString()}`);
    rawRows = Array.isArray(rows) ? rows : [];
    updateStats(rawRows);
    applyFiltersAndRender();
  } catch (e) {
    rawRows = [];
    updateStats(rawRows);
    render([]);
    const empty = document.getElementById("emptyBox");
    if (empty) {
      empty.style.display = "block";
      empty.textContent = `${t("loadFail")}: ${(e && e.message) ? e.message : ""}`;
    }
  } finally {
    if (btn) btn.disabled = false;
  }
}

function bindEvents() {
  document.getElementById("btnRefresh")?.addEventListener("click", (e) => {
    e.preventDefault();
    loadLogs();
  });
  document.getElementById("filterEntityType")?.addEventListener("change", loadLogs);
  document.getElementById("filterLimit")?.addEventListener("change", loadLogs);
  document.getElementById("filterReview")?.addEventListener("change", () => {
    applyFiltersAndRender();
  });
  document.getElementById("filterKeyword")?.addEventListener("input", () => {
    applyFiltersAndRender();
  });
}

window.addEventListener("app:locale-changed", () => {
  applyText();
  updateStats(rawRows);
  applyFiltersAndRender();
});

document.addEventListener("DOMContentLoaded", () => {
  applyText();
  bindEvents();
  loadLogs();
});
