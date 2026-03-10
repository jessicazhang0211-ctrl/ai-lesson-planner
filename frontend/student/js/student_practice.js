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
      const meta = `${item.status === "completed" ? "已完成" : "待完成"} · ${item.created_at || ""}`;
      return `
        <div class="task-item">
          <div>
            <div class="task-title">${item.title || "练习"}</div>
            <div class="task-meta">${meta}</div>
          </div>
          <button class="btn">开始</button>
        </div>
      `;
    }).join("");
  } catch {
    box.innerHTML = `<div style="color:#8a8f98;font-size:12px;">(empty)</div>`;
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
    alert("已开始练习");
  });
}

document.addEventListener("DOMContentLoaded", () => {
  requireLogin();
  applySystemSettings();
  loadStudentProfile();
  renderTasks();
  bindPracticeEvents();
});
