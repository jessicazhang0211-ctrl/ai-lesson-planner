let currentPublishId = null;
let currentQuestions = [];
let assignmentStatus = "assigned";
let submissionStatus = "";
let currentAutoResult = {};
let currentAutoScore = null;
let currentTotalScore = null;
let reviewMode = false;

const practiceDoDict = {
  zh: {
    empty: "(空)",
    correct: "正确",
    wrong: "错误",
    partial: "不全对",
    pending: "待批改",
    tfTrue: "正确",
    tfFalse: "错误",
    analysis: "解析",
    correctAnswer: "正确答案",
    teacherScore: "老师评分",
    yourAnswer: "你的答案",
    autoScore: "自动得分",
    totalScore: "总分",
    submitted: "该作业已提交。",
    submittedWithMeta: "该作业已提交。{meta}",
    submittedHint: "可返回练习列表查看状态。",
    savedHint: "已保存，可继续作答后提交。",
    homework: "作业",
    status: "状态",
    loadFailed: "无法加载作业",
    saveFailed: "保存失败",
    saveSuccess: "保存成功",
    submitFailed: "提交失败",
    submitSuccess: "提交成功，已自动批改选择题和填空题",
    graded: "已批改"
  },
  en: {
    empty: "(empty)",
    correct: "Correct",
    wrong: "Wrong",
    partial: "Partial",
    pending: "Pending review",
    tfTrue: "True",
    tfFalse: "False",
    analysis: "Explanation",
    correctAnswer: "Correct answer",
    teacherScore: "Teacher score",
    yourAnswer: "Your answer",
    autoScore: "Auto score",
    totalScore: "Total score",
    submitted: "This assignment has been submitted.",
    submittedWithMeta: "This assignment has been submitted. {meta}",
    submittedHint: "You can return to the list to check status.",
    savedHint: "Saved. You can continue and submit later.",
    homework: "Homework",
    status: "Status",
    loadFailed: "Unable to load assignment",
    saveFailed: "Save failed",
    saveSuccess: "Saved",
    submitFailed: "Submit failed",
    submitSuccess: "Submitted. Objective questions were graded automatically.",
    graded: "graded"
  }
};
const i18n = window.I18N || null;
if (i18n) i18n.registerDict("studentPracticeDo", practiceDoDict);

function getLocale() {
  return i18n ? i18n.getLocale() : (localStorage.getItem("locale") || "zh");
}

function t(key) {
  if (i18n) return i18n.t("studentPracticeDo", key, key);
  const locale = getLocale();
  return (practiceDoDict[locale] && practiceDoDict[locale][key]) || practiceDoDict.zh[key] || key;
}

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
    body.innerHTML = `<div style='color:#8a8f98;font-size:12px;'>${t("empty")}</div>`;
    return;
  }
  const draft = draftAnswers || {};
  const locked = assignmentStatus === "completed";
  body.innerHTML = questions.map((q, idx) => {
    const qid = q.id || `q${idx + 1}`;
    const type = (q.type || "").toLowerCase();
    const result = getDisplayResult(q, qid);
    const statusTag = result ? `<span class="q-status ${result}">${result === "correct" ? t("correct") : (result === "wrong" ? t("wrong") : (result === "partial" ? t("partial") : t("pending")) )}</span>` : "";
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
          <input type="radio" name="${qid}" value="true" ${v === "true" ? "checked" : ""} ${locked ? "disabled" : ""} /> ${t("tfTrue")}
        </label>
        <label class="answer-option">
          <input type="radio" name="${qid}" value="false" ${v === "false" ? "checked" : ""} ${locked ? "disabled" : ""} /> ${t("tfFalse")}
        </label>
      `;
    } else if (type === "fill") {
      const v = typeof draft[qid] === "string" ? draft[qid] : "";
      inputHtml = `<input type="text" name="${qid}" class="answer-input" value="${v}" ${locked ? "disabled" : ""} />`;
    } else {
      const v = typeof draft[qid] === "string" ? draft[qid] : "";
      inputHtml = `<textarea name="${qid}" class="answer-text" ${locked ? "readonly" : ""}>${v}</textarea>`;
    }
    const analysisHtml = (reviewMode && result !== "correct" && q.analysis) ? `<div class="review-analysis">${t("analysis")}: ${q.analysis}</div>` : "";
    const answerHtml = (reviewMode && result !== "correct" && q.answer != null) ? `<div class="review-meta">${t("correctAnswer")}: ${q.answer}</div>` : "";
    const teacherScoreHtml = (reviewMode && q.teacher_score != null) ? `<div class="review-meta">${t("teacherScore")}: ${q.teacher_score}</div>` : "";
    return `
      <div class="question-item">
        <div class="question-title">${idx + 1}. ${q.stem || ""} ${statusTag}</div>
        ${reviewMode ? `<div class="review-meta">${t("yourAnswer")}: ${draft[qid] ?? "--"}</div>` : ""}
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
    const scoreText = typeof currentAutoScore === "number" ? `${t("autoScore")} ${currentAutoScore}` : "";
    const totalText = typeof currentTotalScore === "number" ? `${t("totalScore")} ${currentTotalScore}` : "";
    const meta = [scoreText, totalText].filter(Boolean).join(" · ");
    setTip(meta ? t("submittedWithMeta").replace("{meta}", meta) : `${t("submitted")} ${t("submittedHint")}`);
  } else if (assignmentStatus === "saved") {
    setTip(t("savedHint"));
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
    if (title) title.textContent = data.title || t("homework");
    if (meta) {
      const statusText = submissionStatus ? `${t("status")}: ${submissionStatus}` : "";
      const totalText = typeof currentTotalScore === "number" ? `${t("totalScore")}: ${currentTotalScore}` : "";
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
    alert(t("loadFailed"));
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
      alert(data.message || t("saveFailed"));
      return;
    }
    assignmentStatus = "saved";
    submissionStatus = "saved";
    setTip(t("savedHint"));
    alert(t("saveSuccess"));
  } catch {
    alert(t("saveFailed"));
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
      alert(data.message || t("submitFailed"));
      return;
    }
    assignmentStatus = "completed";
    submissionStatus = data.status || t("graded");
    currentAutoResult = data.auto_result || {};
    currentAutoScore = data.auto_score;
    currentTotalScore = data.total_score;
    await loadReviewDetail();
    alert(t("submitSuccess"));
  } catch {
    alert(t("submitFailed"));
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
