function renderTasks() {
  const tasks = [
    { title: "分数比较练习", meta: "数学 · 10 题 · 截止本周五" },
    { title: "英语单词填空", meta: "英语 · 15 题 · 截止周三" }
  ];
  const box = document.getElementById("taskList");
  if (!box) return;
  box.innerHTML = tasks.map(item => {
    return `
      <div class="task-item">
        <div>
          <div class="task-title">${item.title}</div>
          <div class="task-meta">${item.meta}</div>
        </div>
        <button class="btn">开始</button>
      </div>
    `;
  }).join("");
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
