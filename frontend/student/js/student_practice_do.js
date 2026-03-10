let currentPublishId = null;
let currentQuestions = [];
let assignmentStatus = "assigned";
let submissionStatus = "";
let currentAutoResult = {};
let currentAutoScore = null;
let currentTotalScore = null;

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
    const result = currentAutoResult && currentAutoResult[qid] ? currentAutoResult[qid] : "";
    const statusTag = result ? `<span class="q-status ${result}">${result === "correct" ? "正确" : (result === "wrong" ? "错误" : "待批改")}</span>` : "";
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
    return `
      <div class="question-item">
        <div class="question-title">${idx + 1}. ${q.stem || ""} ${statusTag}</div>
        ${inputHtml}
      </div>
    `;
  }).join("");
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

    renderExercise(currentQuestions, data.draft_answers || {});
    updateActionState();
  } catch {
    alert("无法加载作业");
    openBack();
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
    renderExercise(currentQuestions, answers);
    updateActionState();
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
