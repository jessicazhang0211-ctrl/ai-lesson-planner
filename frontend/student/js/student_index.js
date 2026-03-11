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
        title: a.title || "练习",
        meta: `${a.status === "completed" ? "已完成" : "待完成"} · ${a.created_at || ""}`
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
