async function renderLessons() {
  const box = document.getElementById("lessonList");
  if (!box) return;
  try {
    const lessons = await apiGet("/api/student/lessons");
    if (!lessons.length) {
      box.innerHTML = `<div style="color:#8a8f98;font-size:12px;">(empty)</div>`;
      return;
    }
    box.innerHTML = lessons.map(item => {
      const meta = item.published_at || item.created_at || "";
      return `
        <div class="lesson-item">
          <div>
            <div class="lesson-title">${item.title || "教案"}</div>
            <div class="lesson-sub">${meta}</div>
          </div>
          <button class="btn" data-id="${item.id}">查看</button>
        </div>
      `;
    }).join("");
  } catch {
    box.innerHTML = `<div style="color:#8a8f98;font-size:12px;">(empty)</div>`;
  }
}

function bindLessonEvents() {
  document.getElementById("btnRefreshLessons")?.addEventListener("click", renderLessons);
}

document.addEventListener("DOMContentLoaded", () => {
  requireLogin();
  applySystemSettings();
  loadStudentProfile();
  renderLessons();
  bindLessonEvents();
});
