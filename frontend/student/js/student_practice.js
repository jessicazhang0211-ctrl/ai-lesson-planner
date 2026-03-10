let currentPublishId = null;
let currentQuestions = [];

async function renderTasks() {
  const box = document.getElementById("taskList");
  if (!box) return;
  try {
    const assignments = await apiGet("/api/student/assignments");
    const tasks = (assignments || []).filter(a => a.resource_type === "exercise");
    if (!tasks.length) {
      box.innerHTML = `<div style="color:#8a8f98;font-size:12px;">(empty)</div>`;
      return;
    }
    box.innerHTML = tasks.map(item => {
      const done = item.status === "completed";
      const saved = item.status === "saved";
      const meta = `${done ? "已完成" : (saved ? "已保存" : "待完成")} · ${item.created_at || ""}`;
      const btnText = done ? "查看" : (saved ? "继续" : "开始");
      return `
        <div class="task-item" data-publish-id="${item.publish_id}">
          <div>
            <div class="task-title">${item.title || "练习"}</div>
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
    box.innerHTML = `<div style="color:#8a8f98;font-size:12px;">(empty)</div>`;
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
      alert("暂无可练习的作业");
      return;
    }
    const pending = tasks.find(t => t.status !== "completed") || tasks[0];
    openExercisePage(Number(pending.publish_id));
  } catch {
    alert("无法开始练习");
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
