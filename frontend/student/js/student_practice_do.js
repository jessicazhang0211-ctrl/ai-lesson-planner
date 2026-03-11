let currentPublishId = null;
let currentQuestions = [];
let assignmentStatus = "assigned";
let submissionStatus = "";
let currentAutoResult = {};
let currentAutoScore = null;
let currentTotalScore = null;
let reviewMode = false;

function getPublishId() {
  const params = new URLSearchParams(window.location.search);
  const raw = params.get("publish_id");
  const id = Number(raw || 0);
  return Number.isFinite(id) && id > 0 ? id : null;
}

function openBack() {
  window.location.href = "./practice.html";
}

function setTip(text) {
  const el = document.getElementById("exerciseTip");
  if (!el) return;
  el.textContent = text || "";
}

function renderExercise(questions, draftAnswers) {
  const body = document.getElementById("exerciseBody");
  if (!body) return;
  if (!questions.length) {
    body.innerHTML = "<div style='color:#8a8f98;font-size:12px;'>(empty)</div>";
    return;
  }
  const draft = draftAnswers || {};
  const locked = assignmentStatus === "completed";
  body.innerHTML = questions.map((q, idx) => {
    const qid = q.id || `q${idx + 1}`;
    const type = (q.type || "").toLowerCase();
    const result = getDisplayResult(q, qid);
    const statusTag = result ? `<span class="q-status ${result}">${result === "correct" ? "正确" : (result === "wrong" ? "错误" : (result === "partial" ? "不全对" : "待批改"))}</span>` : "";
    let inputHtml = "";
    if (type === "single" && Array.isArray(q.options)) {
      inputHtml = q.options.map((op, i) => {
        const label = String.fromCharCode(65 + i);
        const checked = draft[qid] === label ? "checked" : "";
        return `
          <label class="answer-option">
            <input type="radio" name="${qid}" value="${label}" ${checked} ${locked ? "disabled" : ""} /> ${label}. ${op}
          </label>
        `;
      }).join("");
    } else if (type === "multi" && Array.isArray(q.options)) {
      const chosen = Array.isArray(draft[qid]) ? draft[qid] : [];
      inputHtml = q.options.map((op, i) => {
        const label = String.fromCharCode(65 + i);
        const checked = chosen.includes(label) ? "checked" : "";
        return `
          <label class="answer-option">
            <input type="checkbox" name="${qid}" value="${label}" ${checked} ${locked ? "disabled" : ""} /> ${label}. ${op}
          </label>
        `;
      }).join("");
    } else if (type === "true_false") {
      const v = String(draft[qid] || "");
      inputHtml = `
        <label class="answer-option">
          <input type="radio" name="${qid}" value="true" ${v === "true" ? "checked" : ""} ${locked ? "disabled" : ""} /> 正确
        </label>
        <label class="answer-option">
          <input type="radio" name="${qid}" value="false" ${v === "false" ? "checked" : ""} ${locked ? "disabled" : ""} /> 错误
        </label>
      `;
    } else if (type === "fill") {
      const v = typeof draft[qid] === "string" ? draft[qid] : "";
      inputHtml = `<input type="text" name="${qid}" class="answer-input" value="${v}" ${locked ? "disabled" : ""} />`;
    } else {
      const v = typeof draft[qid] === "string" ? draft[qid] : "";
      inputHtml = `<textarea name="${qid}" class="answer-text" ${locked ? "readonly" : ""}>${v}</textarea>`;
    }
    const analysisHtml = (reviewMode && result !== "correct" && q.analysis) ? `<div class="review-analysis">解析：${q.analysis}</div>` : "";
    const answerHtml = (reviewMode && result !== "correct" && q.answer != null) ? `<div class="review-meta">正确答案：${q.answer}</div>` : "";
    const teacherScoreHtml = (reviewMode && q.teacher_score != null) ? `<div class="review-meta">老师评分：${q.teacher_score}</div>` : "";
    return `
      <div class="question-item">
        <div class="question-title">${idx + 1}. ${q.stem || ""} ${statusTag}</div>
        ${reviewMode ? `<div class="review-meta">你的答案：${draft[qid] ?? "--"}</div>` : ""}
        ${inputHtml}
        ${reviewMode ? answerHtml : ""}
        ${reviewMode ? teacherScoreHtml : ""}
        ${reviewMode ? analysisHtml : ""}
      </div>
    `;
  }).join("");
}

function getDisplayResult(q, qid) {
  const type = (q.type || "").toLowerCase();
  if (type === "short" || type === "essay") {
    const maxScore = Number(q.score || 0);
    if (q.teacher_score == null || Number.isNaN(Number(q.teacher_score))) {
      return currentAutoResult && currentAutoResult[qid] ? currentAutoResult[qid] : "pending";
    }
    const ts = Number(q.teacher_score || 0);
    if (ts <= 0) return "wrong";
    if (maxScore > 0 && ts < maxScore) return "partial";
    return "correct";
  }
  return currentAutoResult && currentAutoResult[qid] ? currentAutoResult[qid] : "pending";
}

function collectAnswers() {
  const answers = {};
  currentQuestions.forEach((q, idx) => {
    const qid = q.id || `q${idx + 1}`;
    const type = (q.type || "").toLowerCase();
    if (type === "multi") {
      const checked = Array.from(document.querySelectorAll(`input[name='${qid}']:checked`)).map(i => i.value);
      answers[qid] = checked;
      return;
    }
    if (type === "single" || type === "true_false") {
      const val = document.querySelector(`input[name='${qid}']:checked`)?.value || "";
      answers[qid] = val;
      return;
    }
    const val = document.querySelector(`[name='${qid}']`)?.value || "";
    answers[qid] = val;
  });
  return answers;
}

function updateActionState() {
  const saveBtn = document.getElementById("exerciseSave");
  const submitBtn = document.getElementById("exerciseSubmit");
  if (!saveBtn || !submitBtn) return;

  const done = assignmentStatus === "completed";
  saveBtn.disabled = done;
  submitBtn.disabled = done;

  if (done) {
    const scoreText = typeof currentAutoScore === "number" ? `自动得分 ${currentAutoScore}` : "";
    const totalText = typeof currentTotalScore === "number" ? `总分 ${currentTotalScore}` : "";
    const meta = [scoreText, totalText].filter(Boolean).join(" · ");
    setTip(meta ? `该作业已提交。${meta}` : "该作业已提交。可返回练习列表查看状态。");
  } else if (assignmentStatus === "saved") {
    setTip("已保存，可继续作答后提交。");
  } else {
    setTip("");
  }
}

async function loadExercise() {
  const publishId = getPublishId();
  if (!publishId) {
    openBack();
    return;
  }
  try {
    const data = await apiGet(`/api/student/exercises/${publishId}`);
    currentPublishId = publishId;
    currentQuestions = data.questions || [];
    assignmentStatus = data.assignment_status || "assigned";
    submissionStatus = data.submission_status || "";
    currentAutoResult = data.auto_result || {};
    currentAutoScore = data.auto_score;
    currentTotalScore = data.total_score;

    const title = document.getElementById("exerciseTitle");
    const meta = document.getElementById("exerciseMeta");
    if (title) title.textContent = data.title || "作业";
    if (meta) {
      const statusText = submissionStatus ? `状态：${submissionStatus}` : "";
      const totalText = typeof currentTotalScore === "number" ? `总分：${currentTotalScore}` : "";
      meta.textContent = [statusText, totalText].filter(Boolean).join(" · ");
    }

    if (assignmentStatus === "completed") {
      await loadReviewDetail();
    } else {
      reviewMode = false;
      renderExercise(currentQuestions, data.draft_answers || {});
      updateActionState();
    }
  } catch {
    alert("无法加载作业");
    openBack();
  }
}

async function loadReviewDetail() {
  if (!currentPublishId) return;
  try {
    const detail = await apiGet(`/api/student/review/${currentPublishId}`);
    reviewMode = true;
    currentQuestions = detail.questions || [];
    currentAutoScore = detail.auto_score;
    currentTotalScore = detail.total_score;
    currentAutoResult = {};
    const draft = {};
    currentQuestions.forEach(q => {
      const qid = q.id;
      if (qid) {
        currentAutoResult[qid] = q.result || "";
        draft[qid] = q.student_answer;
      }
    });
    renderExercise(currentQuestions, draft);
    updateActionState();
  } catch {
    renderExercise(currentQuestions, {});
    updateActionState();
  }
}

async function saveExercise() {
  if (!currentPublishId) return;
  const answers = collectAnswers();
  try {
    const res = await fetch(`http://127.0.0.1:5000/api/student/exercises/${currentPublishId}/save`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${localStorage.getItem("auth_token") || ""}`
      },
      body: JSON.stringify({ answers })
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.code !== 0) {
      alert(data.message || "保存失败");
      return;
    }
    assignmentStatus = "saved";
    submissionStatus = "saved";
    setTip("已保存，可继续作答后提交。");
    alert("保存成功");
  } catch {
    alert("保存失败");
  }
}

async function submitExercise() {
  if (!currentPublishId) return;
  const answers = collectAnswers();
  try {
    const res = await fetch(`http://127.0.0.1:5000/api/student/exercises/${currentPublishId}/submit`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${localStorage.getItem("auth_token") || ""}`
      },
      body: JSON.stringify({ answers })
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.code !== 0) {
      alert(data.message || "提交失败");
      return;
    }
    assignmentStatus = "completed";
    submissionStatus = data.status || "graded";
    currentAutoResult = data.auto_result || {};
    currentAutoScore = data.auto_score;
    currentTotalScore = data.total_score;
    await loadReviewDetail();
    alert("提交成功，已自动批改选择题和填空题");
  } catch {
    alert("提交失败");
  }
}

function bindEvents() {
  document.getElementById("btnBack")?.addEventListener("click", openBack);
  document.getElementById("exerciseSave")?.addEventListener("click", saveExercise);
  document.getElementById("exerciseSubmit")?.addEventListener("click", submitExercise);
}

document.addEventListener("DOMContentLoaded", () => {
  requireLogin();
  applySystemSettings();
  loadStudentProfile();
  bindEvents();
  loadExercise();
});
