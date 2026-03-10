let lessonCache = [];

async function renderLessons() {
  const box = document.getElementById("lessonList");
  if (!box) return;
  try {
    const lessons = await apiGet("/api/student/lessons");
    lessonCache = lessons || [];
    if (!lessonCache.length) {
      box.innerHTML = `<div style="color:#8a8f98;font-size:12px;">(empty)</div>`;
      return;
    }
    box.innerHTML = lessonCache.map(item => {
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

    box.querySelectorAll(".btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const id = Number(btn.getAttribute("data-id"));
        openLesson(id);
      });
    });
  } catch {
    box.innerHTML = `<div style="color:#8a8f98;font-size:12px;">(empty)</div>`;
  }
}

function openLesson(id) {
  const modal = document.getElementById("lessonModal");
  const title = document.getElementById("lessonTitle");
  const content = document.getElementById("lessonContent");
  if (!modal || !title || !content) return;
  const item = lessonCache.find(x => x.id === id);
  if (!item) return;
  title.textContent = item.title || "教案";
  content.textContent = item.content || "";
  modal.classList.add("open");
  modal.setAttribute("aria-hidden", "false");
}

function closeLesson() {
  const modal = document.getElementById("lessonModal");
  if (!modal) return;
  modal.classList.remove("open");
  modal.setAttribute("aria-hidden", "true");
}

function bindLessonEvents() {
  document.getElementById("btnRefreshLessons")?.addEventListener("click", renderLessons);
  document.getElementById("lessonClose")?.addEventListener("click", closeLesson);
  document.getElementById("lessonCloseBtn")?.addEventListener("click", closeLesson);
}

document.addEventListener("DOMContentLoaded", () => {
  requireLogin();
  applySystemSettings();
  loadStudentProfile();
  renderLessons();
  bindLessonEvents();
});
