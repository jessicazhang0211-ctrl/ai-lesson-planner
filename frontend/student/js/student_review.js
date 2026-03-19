let reviewList = [];
let currentPublishId = null;
let currentDetail = null;
let filteredList = [];

const reviewDict = {
  zh: {
    pageTitle: "复习 · 学生端",
    heroTitle: "复习与错题",
    heroSub: "已完成作业自动归档，可查看错题解析。",
    btnRefresh: "刷新",
    filterTitleLabel: "作业名称",
    filterTitlePlaceholder: "输入作业名称",
    btnFilter: "筛选",
    listTitle: "已完成作业",
    listSub: "点击查看错题与解析",
    toggleWrongOnly: "只看错题",
    empty: "(空)",
    exercise: "练习",
    view: "查看",
    wrongTitle: "错题解析",
    noWrong: "暂无错题",
    totalScore: "总分",
    status: "状态",
    analysis: "解析",
    yourAnswer: "你的答案",
    correctAnswer: "正确答案",
    teacherScore: "老师评分",
    correct: "正确",
    wrong: "错误",
    partial: "不全对",
    pending: "待批改"
  },
  en: {
    pageTitle: "Review · Student",
    heroTitle: "Review & Wrong Answers",
    heroSub: "Completed assignments are archived for reviewing explanations.",
    btnRefresh: "Refresh",
    filterTitleLabel: "Assignment Title",
    filterTitlePlaceholder: "Enter assignment title",
    btnFilter: "Filter",
    listTitle: "Completed Assignments",
    listSub: "Click to view wrong answers and explanations",
    toggleWrongOnly: "Show wrong answers only",
    empty: "(empty)",
    exercise: "Exercise",
    view: "View",
    wrongTitle: "Wrong Answers Review",
    noWrong: "No wrong answers",
    totalScore: "Total score",
    status: "Status",
    analysis: "Explanation",
    yourAnswer: "Your answer",
    correctAnswer: "Correct answer",
    teacherScore: "Teacher score",
    correct: "Correct",
    wrong: "Wrong",
    partial: "Partial",
    pending: "Pending review"
  }
};
const i18n = window.I18N || null;
if (i18n) i18n.registerDict("studentReview", reviewDict);

function getLocale() {
  return i18n ? i18n.getLocale() : (localStorage.getItem("locale") || "zh");
}

function t(key) {
  if (i18n) return i18n.t("studentReview", key, key);
  const locale = getLocale();
  return (reviewDict[locale] && reviewDict[locale][key]) || reviewDict.zh[key] || key;
}

function applyPageI18n() {
  if (i18n) i18n.applyDataI18n("studentReview", document);
  document.title = t("pageTitle");
}

function renderList() {
  const box = document.getElementById("reviewList");
  if (!box) return;
  if (!filteredList.length) {
    box.innerHTML = `<div style="color:#8a8f98;font-size:12px;">${t("empty")}</div>`;
    return;
  }
  box.innerHTML = filteredList.map(item => {
    const active = currentPublishId === item.publish_id ? "active" : "";
    const meta = `${item.completed_at || item.created_at || ""}`;
    return `
      <div class="task-item ${active}" data-publish-id="${item.publish_id}">
        <div>
          <div class="task-title">${item.title || t("exercise")}</div>
          <div class="task-meta">${item.class_name || ""} · ${meta}</div>
        </div>
        <button class="btn">${t("view")}</button>
      </div>
    `;
  }).join("");

  box.querySelectorAll(".task-item .btn").forEach(btn => {
    btn.addEventListener("click", (e) => {
      const row = e.target.closest(".task-item");
      const publishId = row?.getAttribute("data-publish-id");
      if (publishId) loadDetail(Number(publishId));
    });
  });
}

function applyFilters() {
  const titleKw = (document.getElementById("reviewTitleKeyword")?.value || "").trim();
  filteredList = reviewList.filter(item => {
    if (titleKw && !(item.title || "").includes(titleKw)) return false;
    return true;
  });
  renderList();
  if (filteredList.length && !currentPublishId) {
    loadDetail(Number(filteredList[0].publish_id));
  }
}

function renderDetail() {
  const title = document.getElementById("reviewTitle");
  const meta = document.getElementById("reviewMeta");
  const body = document.getElementById("reviewBody");
  if (!body) return;
  if (!currentDetail) {
    if (title) title.textContent = t("wrongTitle");
    if (meta) meta.textContent = "—";
    body.innerHTML = `<div style="color:#8a8f98;font-size:12px;">${t("empty")}</div>`;
    return;
  }

  const onlyWrong = document.getElementById("toggleWrongOnly")?.checked;
  const questions = currentDetail.questions || [];
  const showList = onlyWrong ? questions.filter(q => getDisplayResult(q) !== "correct") : questions;

  if (title) title.textContent = currentDetail.title || t("wrongTitle");
  if (meta) {
    const score = currentDetail.total_score != null ? `${t("totalScore")}: ${currentDetail.total_score}` : "";
    meta.textContent = [currentDetail.status ? `${t("status")}: ${currentDetail.status}` : "", score].filter(Boolean).join(" · ");
  }

  if (!showList.length) {
    body.innerHTML = `<div style="color:#8a8f98;font-size:12px;">${t("noWrong")}</div>`;
    return;
  }

  body.innerHTML = showList.map((q, idx) => {
    const analysis = q.analysis ? `<div class="review-analysis">${t("analysis")}: ${q.analysis}</div>` : "";
    const studentAns = q.student_answer != null ? `${q.student_answer}` : "";
    const correctAns = q.answer != null ? `${q.answer}` : "";
    const teacherScore = q.teacher_score != null ? `<div class="review-meta">${t("teacherScore")}: ${q.teacher_score}</div>` : "";
    const result = getDisplayResult(q);
    const statusTag = result ? `<span class="q-status ${result}">${result === "correct" ? t("correct") : (result === "wrong" ? t("wrong") : (result === "partial" ? t("partial") : t("pending")) )}</span>` : "";
    return `
      <div class="review-item">
        <div class="question-title">${idx + 1}. ${q.stem || ""} ${statusTag}</div>
        <div class="review-meta">${t("yourAnswer")}: ${studentAns || "--"}</div>
        ${result !== "correct" ? `<div class="review-meta">${t("correctAnswer")}: ${correctAns || "--"}</div>` : ""}
        ${teacherScore}
        ${result !== "correct" ? analysis : ""}
      </div>
    `;
  }).join("");
}

function getDisplayResult(q) {
  const type = (q.type || "").toLowerCase();
  if (type === "short" || type === "essay") {
    const maxScore = Number(q.score || 0);
    if (q.teacher_score == null || Number.isNaN(Number(q.teacher_score))) return q.result || "pending";
    const ts = Number(q.teacher_score || 0);
    if (ts <= 0) return "wrong";
    if (maxScore > 0 && ts < maxScore) return "partial";
    return "correct";
  }
  return q.result || "pending";
}

async function loadList() {
  try {
    const assignmentsResp = await apiGet("/api/student/assignments");
    const assignments = normalizeAssignments(assignmentsResp);
    reviewList = (assignments || [])
      .filter(a => a.resource_type === "exercise")
      .filter(a => a.status === "completed");
    applyFilters();
  } catch {
    reviewList = [];
    filteredList = [];
    renderList();
  }
}

async function loadDetail(publishId) {
  currentPublishId = publishId;
  renderList();
  try {
    const detail = await apiGet(`/api/student/review/${publishId}`);
    currentDetail = detail;
    renderDetail();
  } catch {
    currentDetail = null;
    renderDetail();
  }
}

function bindEvents() {
  document.getElementById("btnRefreshReview")?.addEventListener("click", loadList);
  document.getElementById("btnReviewSearch")?.addEventListener("click", applyFilters);
  document.getElementById("toggleWrongOnly")?.addEventListener("change", renderDetail);
}

document.addEventListener("DOMContentLoaded", () => {
  requireLogin();
  applySystemSettings();
  loadStudentProfile();
  applyPageI18n();
  bindEvents();
  loadList();
  if (i18n) {
    i18n.onLocaleChange(() => {
      applyPageI18n();
      applyFilters();
      renderDetail();
    });
  }
});
