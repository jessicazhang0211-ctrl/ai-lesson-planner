let reviewList = [];
let currentPublishId = null;
let currentDetail = null;
let filteredList = [];

function renderList() {
  const box = document.getElementById("reviewList");
  if (!box) return;
  if (!filteredList.length) {
    box.innerHTML = `<div style="color:#8a8f98;font-size:12px;">(empty)</div>`;
    return;
  }
  box.innerHTML = filteredList.map(item => {
    const active = currentPublishId === item.publish_id ? "active" : "";
    const meta = `${item.completed_at || item.created_at || ""}`;
    return `
      <div class="task-item ${active}" data-publish-id="${item.publish_id}">
        <div>
          <div class="task-title">${item.title || "练习"}</div>
          <div class="task-meta">${item.class_name || ""} · ${meta}</div>
        </div>
        <button class="btn">查看</button>
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
    if (title) title.textContent = "错题解析";
    if (meta) meta.textContent = "—";
    body.innerHTML = `<div style="color:#8a8f98;font-size:12px;">(empty)</div>`;
    return;
  }

  const onlyWrong = document.getElementById("toggleWrongOnly")?.checked;
  const questions = currentDetail.questions || [];
  const showList = onlyWrong ? questions.filter(q => getDisplayResult(q) !== "correct") : questions;

  if (title) title.textContent = currentDetail.title || "错题解析";
  if (meta) {
    const score = currentDetail.total_score != null ? `总分：${currentDetail.total_score}` : "";
    meta.textContent = [currentDetail.status ? `状态：${currentDetail.status}` : "", score].filter(Boolean).join(" · ");
  }

  if (!showList.length) {
    body.innerHTML = `<div style="color:#8a8f98;font-size:12px;">暂无错题</div>`;
    return;
  }

  body.innerHTML = showList.map((q, idx) => {
    const analysis = q.analysis ? `<div class="review-analysis">解析：${q.analysis}</div>` : "";
    const studentAns = q.student_answer != null ? `${q.student_answer}` : "";
    const correctAns = q.answer != null ? `${q.answer}` : "";
    const teacherScore = q.teacher_score != null ? `<div class="review-meta">老师评分：${q.teacher_score}</div>` : "";
    const result = getDisplayResult(q);
    const statusTag = result ? `<span class="q-status ${result}">${result === "correct" ? "正确" : (result === "wrong" ? "错误" : (result === "partial" ? "不全对" : "待批改"))}</span>` : "";
    return `
      <div class="review-item">
        <div class="question-title">${idx + 1}. ${q.stem || ""} ${statusTag}</div>
        <div class="review-meta">你的答案：${studentAns || "--"}</div>
        ${result !== "correct" ? `<div class="review-meta">正确答案：${correctAns || "--"}</div>` : ""}
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
    const assignments = await apiGet("/api/student/assignments");
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
  bindEvents();
  loadList();
});
