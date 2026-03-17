const studentHomeDict = {
  zh: {
    empty: "(空)",
    start: "开始",
    exercise: "练习",
    completed: "已完成",
    pending: "待完成"
  },
  en: {
    empty: "(empty)",
    start: "Start",
    exercise: "Exercise",
    completed: "Completed",
    pending: "Pending"
  }
};
const i18n = window.I18N || null;
if (i18n) i18n.registerDict("studentHome", studentHomeDict);

function getLocale() {
  return i18n ? i18n.getLocale() : (localStorage.getItem("locale") || "zh");
}

function t(key) {
  if (i18n) return i18n.t("studentHome", key, key);
  const locale = getLocale();
  return (studentHomeDict[locale] && studentHomeDict[locale][key]) || studentHomeDict.zh[key] || key;
}

function renderList(id, items, type) {
  const box = document.getElementById(id);
  if (!box) return;
  if (!items.length) {
    box.innerHTML = `<div style="color:#8a8f98;font-size:12px;">${t("empty")}</div>`;
    return;
  }
  box.innerHTML = items.map(item => {
    if (type === "task") {
      return `
        <div class="task-item">
          <div>
            <div class="task-title">${item.title}</div>
            <div class="task-meta">${item.meta}</div>
          </div>
          <button class="btn">${t("start")}</button>
        </div>
      `;
    }
    return "";
  }).join("");
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

async function loadHome() {
  try {
    const [assignments, overview] = await Promise.all([
      apiGet("/api/student/assignments"),
      apiGet("/api/student/overview")
    ]);

    const tasks = (assignments || [])
      .filter(a => a.resource_type === "exercise")
      .filter(a => a.status !== "completed")
      .map(a => ({
        title: a.title || t("exercise"),
        meta: `${a.status === "completed" ? t("completed") : t("pending")} · ${a.created_at || ""}`
      }));

    renderList("taskList", tasks, "task");

    setText("kpiTodo", String(overview.todo ?? 0));
    setText("kpiPractice", String(overview.completed ?? 0));
    setText("kpiAccuracy", overview.avg_score != null ? `${overview.avg_score}%` : "--");
    setText("kpiExam", overview.latest_score != null ? String(overview.latest_score) : "--");

    setText("weakSpot", overview.analysis?.weak_spot || "--");
    setText("studyState", overview.analysis?.study_state || "--");
    setText("studyTip", overview.analysis?.study_tip || "--");
  } catch {
    renderList("taskList", [], "task");
  }
}

function bindHomeEvents() {
  document.getElementById("btnQuickPractice")?.addEventListener("click", () => {
    window.location.href = "./practice.html";
  });
  document.getElementById("btnQuickExam")?.addEventListener("click", () => {
    window.location.href = "./review.html";
  });
  document.getElementById("btnRefreshTasks")?.addEventListener("click", loadHome);
}

document.addEventListener("DOMContentLoaded", () => {
  requireLogin();
  applySystemSettings();
  loadStudentProfile();
  loadHome();
  bindHomeEvents();
});
