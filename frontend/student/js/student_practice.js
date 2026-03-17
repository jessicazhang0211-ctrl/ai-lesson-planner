let currentPublishId = null;
let currentQuestions = [];

const practiceDict = {
  zh: {
    empty: "(空)",
    completed: "已完成",
    saved: "已保存",
    pending: "待完成",
    view: "查看",
    continue: "继续",
    start: "开始",
    exercise: "练习",
    noTask: "暂无可练习的作业",
    startFailed: "无法开始练习"
  },
  en: {
    empty: "(empty)",
    completed: "Completed",
    saved: "Saved",
    pending: "Pending",
    view: "View",
    continue: "Continue",
    start: "Start",
    exercise: "Exercise",
    noTask: "No available assignments",
    startFailed: "Unable to start practice"
  }
};
const i18n = window.I18N || null;
if (i18n) i18n.registerDict("studentPractice", practiceDict);

function getLocale() {
  return i18n ? i18n.getLocale() : (localStorage.getItem("locale") || "zh");
}

function t(key) {
  if (i18n) return i18n.t("studentPractice", key, key);
  const locale = getLocale();
  return (practiceDict[locale] && practiceDict[locale][key]) || practiceDict.zh[key] || key;
}

async function renderTasks() {
  const box = document.getElementById("taskList");
  if (!box) return;
  try {
    const assignments = await apiGet("/api/student/assignments");
    const tasks = (assignments || [])
      .filter(a => a.resource_type === "exercise")
      .filter(a => a.status !== "completed");
    if (!tasks.length) {
      box.innerHTML = `<div style="color:#8a8f98;font-size:12px;">${t("empty")}</div>`;
      return;
    }
    box.innerHTML = tasks.map(item => {
      const done = item.status === "completed";
      const saved = item.status === "saved";
      const meta = `${done ? t("completed") : (saved ? t("saved") : t("pending"))} · ${item.created_at || ""}`;
      const btnText = done ? t("view") : (saved ? t("continue") : t("start"));
      return `
        <div class="task-item" data-publish-id="${item.publish_id}">
          <div>
            <div class="task-title">${item.title || t("exercise")}</div>
            <div class="task-meta">${meta}</div>
          </div>
          <button class="btn">${btnText}</button>
        </div>
      `;
    }).join("");

    box.querySelectorAll(".task-item .btn").forEach(btn => {
      btn.addEventListener("click", async (e) => {
        const row = e.target.closest(".task-item");
        const publishId = row?.getAttribute("data-publish-id");
        if (publishId) openExercisePage(Number(publishId));
      });
    });
  } catch {
    box.innerHTML = `<div style="color:#8a8f98;font-size:12px;">${t("empty")}</div>`;
  }
}

function openExercisePage(publishId) {
  window.location.href = `./practice_do.html?publish_id=${publishId}`;
}

async function startQuickPractice() {
  try {
    const assignments = await apiGet("/api/student/assignments");
    const tasks = (assignments || []).filter(a => a.resource_type === "exercise");
    if (!tasks.length) {
      alert(t("noTask"));
      return;
    }
    const pending = tasks.find(t => t.status !== "completed") || tasks[0];
    openExercisePage(Number(pending.publish_id));
  } catch {
    alert(t("startFailed"));
  }
}

function openPracticeModal() {
  const modal = document.getElementById("practiceModal");
  if (!modal) return;
  modal.classList.add("open");
  modal.setAttribute("aria-hidden", "false");
}

function closePracticeModal() {
  const modal = document.getElementById("practiceModal");
  if (!modal) return;
  modal.classList.remove("open");
  modal.setAttribute("aria-hidden", "true");
}

function bindPracticeEvents() {
  document.getElementById("btnQuickPractice")?.addEventListener("click", openPracticeModal);
  document.getElementById("btnRefreshTasks")?.addEventListener("click", renderTasks);
  document.getElementById("practiceClose")?.addEventListener("click", closePracticeModal);
  document.getElementById("practiceCloseBtn")?.addEventListener("click", closePracticeModal);
  document.getElementById("practiceCancel")?.addEventListener("click", closePracticeModal);
  document.getElementById("practiceStart")?.addEventListener("click", () => {
    closePracticeModal();
    startQuickPractice();
  });

}

document.addEventListener("DOMContentLoaded", () => {
  requireLogin();
  applySystemSettings();
  loadStudentProfile();
  renderTasks();
  bindPracticeEvents();
});
