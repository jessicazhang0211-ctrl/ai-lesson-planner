const API_BASE = "http://127.0.0.1:5000";

let selectedSubmissionId = null;
let reviewList = [];
let currentDetail = null;
let viewMode = "pending";
let classOptions = [];

function getToken() {
  return localStorage.getItem("auth_token") || "";
}

async function apiGet(path) {
  const token = getToken();
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Authorization": `Bearer ${token}` }
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.code !== 0) throw new Error(data.message || "api error");
  return data.data;
}

function getLoginUser() {
  try {
    return JSON.parse(localStorage.getItem("login_user") || "null");
  } catch {
    return null;
  }
}

async function apiGetWithUser(path) {
  const token = getToken();
  const user = getLoginUser();
  const headers = { "Authorization": `Bearer ${token}` };
  if (user && user.id) headers["X-User-Id"] = String(user.id);
  const res = await fetch(`${API_BASE}${path}`, { headers });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.code !== 0) throw new Error(data.message || "api error");
  return data.data;
}

async function apiPost(path, payload) {
  const token = getToken();
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${token}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload || {})
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.code !== 0) throw new Error(data.message || "api error");
  return data.data;
}

function renderList() {
  const box = document.getElementById("reviewItems");
  const count = document.getElementById("reviewCount");
  if (!box || !count) return;

  count.textContent = String(reviewList.length);
  if (!reviewList.length) {
    box.innerHTML = `<div style="color:#8a8f98;font-size:12px;">(empty)</div>`;
    return;
  }

  box.innerHTML = reviewList.map(item => {
    const active = selectedSubmissionId === item.submission_id ? "active" : "";
    return `
      <div class="review-item ${active}" data-id="${item.submission_id}">
        <div class="review-item-title">${item.title || ""}</div>
        <div class="review-item-meta">${item.class_name || ""} · ${item.student_name || ""} · ${item.created_at || ""}</div>
        <div class="review-item-meta">自动得分：${item.auto_score ?? 0}${item.total_score != null ? ` · 总分：${item.total_score}` : ""}${item.teacher_comment ? ` · 评语：${item.teacher_comment}` : ""}</div>
      </div>
    `;
  }).join("");

  box.querySelectorAll(".review-item").forEach(row => {
    row.addEventListener("click", () => {
      const id = Number(row.getAttribute("data-id"));
      selectSubmission(id);
    });
  });
}

function setDetailEmpty(show) {
  const empty = document.getElementById("detailEmpty");
  if (!empty) return;
  empty.style.display = show ? "flex" : "none";
}

function calcTeacherTotal() {
  const inputs = document.querySelectorAll(".teacher-score");
  let total = 0;
  inputs.forEach(input => {
    const v = Number(input.value || 0);
    if (!Number.isNaN(v)) total += v;
  });
  const totalEl = document.getElementById("teacherTotal");
  if (totalEl) totalEl.textContent = String(total);
  return total;
}

async function selectSubmission(id) {
  selectedSubmissionId = id;
  renderList();
  setDetailEmpty(false);

  const title = document.getElementById("detailTitle");
  const meta = document.getElementById("detailMeta");
  const body = document.getElementById("reviewBody");
  const commentInput = document.getElementById("teacherComment");

  try {
    const detail = await apiGet(`/api/resource/review/${id}`);
    if (title) title.textContent = detail.title || "";
    if (meta) {
      const commentText = detail.teacher_comment ? `评语：${detail.teacher_comment}` : "";
      meta.textContent = [`自动得分：${detail.auto_score ?? 0}`, `状态：${detail.status}`, commentText]
        .filter(Boolean)
        .join(" · ");
    }
    if (commentInput) commentInput.value = detail.teacher_comment || "";
    currentDetail = detail;

    if (body) {
      const questions = detail.questions || [];
      body.innerHTML = questions.map((q, idx) => {
        const isSubjective = !!q.is_subjective;
        const maxScore = q.score ?? 0;
        const value = q.teacher_score ?? 0;
        const scoreRow = isSubjective ? `
          <div class="review-score-row">
            <label>评分</label>
            <input type="number" class="teacher-score" data-qid="${q.id}" min="0" max="${maxScore}" value="${value}" />
            <span class="review-score-hint">满分 ${maxScore}</span>
          </div>
        ` : "";
        return `
          <div class="review-question">
            <div class="review-question-title">${idx + 1}. ${q.stem || ""}</div>
            <div class="review-question-meta">学生作答：${q.student_answer ?? ""}</div>
            <div class="review-question-meta">参考答案：${q.answer ?? ""}</div>
            <div class="review-question-meta">题型：${q.type || ""} · 分值：${maxScore}</div>
            ${scoreRow}
          </div>
        `;
      }).join("");

      body.querySelectorAll(".teacher-score").forEach(input => {
        if (input.disabled) return;
        input.addEventListener("input", () => {
          const max = Number(input.getAttribute("max") || 0);
          let v = Number(input.value || 0);
          if (Number.isNaN(v)) v = 0;
          if (v < 0) v = 0;
          if (max && v > max) v = max;
          input.value = String(v);
          calcTeacherTotal();
        });
      });
      calcTeacherTotal();
    }
  } catch {
    setDetailEmpty(true);
  }
}

async function loadReviewList() {
  try {
    if (viewMode === "pending") {
      reviewList = await apiGet("/api/resource/review?status=pending_review");
    } else {
      const classId = document.getElementById("filterClass")?.value || "";
      const student = (document.getElementById("filterStudent")?.value || "").trim();
      const title = (document.getElementById("filterTitle")?.value || "").trim();
      const params = new URLSearchParams();
      if (classId) params.set("class_id", classId);
      if (student) params.set("student", student);
      if (title) params.set("title", title);
      const qs = params.toString();
      reviewList = await apiGet(`/api/resource/review/history${qs ? `?${qs}` : ""}`);
    }
    renderList();
  } catch {
    reviewList = [];
    renderList();
  }
}

function setViewMode(mode) {
  viewMode = mode;
  const filters = document.getElementById("historyFilters");
  const title = document.getElementById("reviewListTitle");
  const tabPending = document.getElementById("tabPending");
  const tabHistory = document.getElementById("tabHistory");
  const submitBtn = document.getElementById("btnSubmitScore");

  if (filters) filters.style.display = mode === "history" ? "grid" : "none";
  if (title) title.textContent = mode === "history" ? "历史批改" : "待批改列表";
  if (tabPending) tabPending.classList.toggle("primary", mode === "pending");
  if (tabHistory) tabHistory.classList.toggle("primary", mode === "history");
  if (submitBtn) submitBtn.style.display = mode === "history" ? "none" : "inline-flex";
  setDetailEmpty(true);
  loadReviewList();
}

async function loadClasses() {
  try {
    classOptions = await apiGetWithUser("/api/class/?status=all");
  } catch {
    classOptions = [];
  }
  const select = document.getElementById("filterClass");
  if (!select) return;
  const options = ["<option value=\"\">全部</option>"]
    .concat(classOptions.map(c => `<option value="${c.id}">${c.name}</option>`));
  select.innerHTML = options.join("");
}

function bindEvents() {
  document.getElementById("btnRefresh")?.addEventListener("click", loadReviewList);
  document.getElementById("tabPending")?.addEventListener("click", () => setViewMode("pending"));
  document.getElementById("tabHistory")?.addEventListener("click", () => setViewMode("history"));
  document.getElementById("btnSearch")?.addEventListener("click", loadReviewList);
  document.getElementById("btnSubmitScore")?.addEventListener("click", async () => {
    if (!selectedSubmissionId) return;
    const teacherComment = document.getElementById("teacherComment").value || "";
    const scores = {};
    document.querySelectorAll(".teacher-score").forEach(input => {
      const qid = input.getAttribute("data-qid");
      if (!qid) return;
      scores[qid] = Number(input.value || 0);
    });
    try {
      await apiPost(`/api/resource/review/${selectedSubmissionId}/score`, { scores, teacher_comment: teacherComment });
      await loadReviewList();
      setDetailEmpty(true);
    } catch (e) {
      alert("提交失败");
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  bindEvents();
  loadClasses();
  setViewMode("pending");
});
