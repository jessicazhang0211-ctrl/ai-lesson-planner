function renderLessons() {
  const lessons = [
    { title: "分数的初步认识", meta: "数学 · 周一发布" },
    { title: "阅读理解技巧", meta: "语文 · 周二发布" }
  ];
  const box = document.getElementById("lessonList");
  if (!box) return;
  box.innerHTML = lessons.map(item => {
    return `
      <div class="lesson-item">
        <div>
          <div class="lesson-title">${item.title}</div>
          <div class="lesson-sub">${item.meta}</div>
        </div>
        <button class="btn">查看</button>
      </div>
    `;
  }).join("");
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
