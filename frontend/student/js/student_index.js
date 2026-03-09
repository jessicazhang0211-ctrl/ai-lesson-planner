function renderList(id, items, type) {
  const box = document.getElementById(id);
  if (!box) return;
  if (!items.length) {
    box.innerHTML = `<div style="color:#8a8f98;font-size:12px;">(empty)</div>`;
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
          <button class="btn">开始</button>
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

function seedHome() {
  const tasks = [
    { title: "分数比较练习", meta: "数学 · 10 题 · 截止本周五" },
    { title: "英语单词填空", meta: "英语 · 15 题 · 截止周三" }
  ];

  renderList("taskList", tasks, "task");

  setText("kpiTodo", String(tasks.length));
  setText("kpiPractice", "120");
  setText("kpiAccuracy", "86%");
  setText("kpiExam", "92");

  setText("weakSpot", "分数比较 / 应用题");
  setText("studyState", "保持稳定，继续巩固");
  setText("studyTip", "建议每天完成 10 题基础练习");
}

function bindHomeEvents() {
  document.getElementById("btnQuickPractice")?.addEventListener("click", () => {
    window.location.href = "./practice.html";
  });
  document.getElementById("btnQuickExam")?.addEventListener("click", () => {
    window.location.href = "./exam.html";
  });
  document.getElementById("btnRefreshTasks")?.addEventListener("click", seedHome);
}

document.addEventListener("DOMContentLoaded", () => {
  requireLogin();
  applySystemSettings();
  loadStudentProfile();
  seedHome();
  bindHomeEvents();
});
