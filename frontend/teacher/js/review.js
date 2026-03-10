const API_BASE = "http://127.0.0.1:5000";

let selectedSubmissionId = null;
let reviewList = [];

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
        <div class="review-item-meta">${item.class_name || ""} · ${item.created_at || ""}</div>
        <div class="review-item-meta">自动得分：${item.auto_score ?? 0}</div>
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

async function selectSubmission(id) {
  selectedSubmissionId = id;
  renderList();
  setDetailEmpty(false);

  const title = document.getElementById("detailTitle");
  const meta = document.getElementById("detailMeta");
  const body = document.getElementById("reviewBody");
  const scoreInput = document.getElementById("teacherScore");
  const commentInput = document.getElementById("teacherComment");

  try {
    const detail = await apiGet(`/api/resource/review/${id}`);
    if (title) title.textContent = detail.title || "";
    if (meta) meta.textContent = `自动得分：${detail.auto_score ?? 0} · 状态：${detail.status}`;
    if (scoreInput) scoreInput.value = detail.teacher_score ?? 0;
    if (commentInput) commentInput.value = "";

    if (body) {
      const questions = detail.questions || [];
      body.innerHTML = questions.map((q, idx) => {
        return `
          <div class="review-question">
            <div class="review-question-title">${idx + 1}. ${q.stem || ""}</div>
            <div class="review-question-meta">学生作答：${q.student_answer ?? ""}</div>
            <div class="review-question-meta">参考答案：${q.answer ?? ""}</div>
            <div class="review-question-meta">题型：${q.type || ""} · 分值：${q.score ?? 0}</div>
          </div>
        `;
      }).join("");
    }
  } catch {
    setDetailEmpty(true);
  }
}

async function loadReviewList() {
  try {
    reviewList = await apiGet("/api/resource/review?status=pending_review");
    renderList();
  } catch {
    reviewList = [];
    renderList();
  }
}

function bindEvents() {
  document.getElementById("btnRefresh")?.addEventListener("click", loadReviewList);
  document.getElementById("btnSubmitScore")?.addEventListener("click", async () => {
    if (!selectedSubmissionId) return;
    const teacherScore = Number(document.getElementById("teacherScore").value || 0);
    const teacherComment = document.getElementById("teacherComment").value || "";
    try {
      await apiPost(`/api/resource/review/${selectedSubmissionId}/score`, { teacher_score: teacherScore, teacher_comment: teacherComment });
      await loadReviewList();
      setDetailEmpty(true);
    } catch (e) {
      alert("提交失败");
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  loadReviewList();
  bindEvents();
});
