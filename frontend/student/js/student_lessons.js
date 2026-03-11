let lessonCache = [];
let selectedLessonId = null;

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
      const active = selectedLessonId === item.id ? "active" : "";
      return `
        <div class="lesson-item ${active}">
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

    if (lessonCache.length && !selectedLessonId) {
      openLesson(lessonCache[0].id);
    }
  } catch {
    box.innerHTML = `<div style="color:#8a8f98;font-size:12px;">(empty)</div>`;
  }
}

function openLesson(id) {
  const title = document.getElementById("lessonTitle");
  const content = document.getElementById("lessonContent");
  const meta = document.getElementById("lessonMeta");
  const empty = document.getElementById("lessonEmpty");
  if (!title || !content || !meta || !empty) return;
  const item = lessonCache.find(x => x.id === id);
  if (!item) return;
  selectedLessonId = id;
  title.textContent = item.title || "教案";
  content.textContent = item.content || "";
  meta.textContent = item.published_at || item.created_at || "";
  empty.style.display = item.content ? "none" : "flex";
  renderLessons();
}

function downloadLessonPdf() {
  const item = lessonCache.find(x => x.id === selectedLessonId);
  if (!item) return;
  const jspdf = window.jspdf;
  if (!jspdf || !jspdf.jsPDF) return;
  const doc = new jspdf.jsPDF({ unit: "pt", format: "a4" });
  const title = item.title || "教案";
  const content = item.content || "";
  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const marginX = 40;
  const marginTop = 48;
  const lineHeight = 16;
  doc.setFont("helvetica", "bold");
  doc.setFontSize(16);
  doc.text(title, marginX, marginTop);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(11);
  const textLines = doc.splitTextToSize(content, pageWidth - marginX * 2);
  let cursorY = marginTop + 24;
  textLines.forEach(line => {
    if (cursorY + lineHeight > pageHeight - marginTop) {
      doc.addPage();
      cursorY = marginTop;
    }
    doc.text(line, marginX, cursorY);
    cursorY += lineHeight;
  });
  const safeTitle = title.replaceAll(/[\\/:*?"<>|]/g, "_");
  doc.save(`${safeTitle}.pdf`);
}

function bindLessonEvents() {
  document.getElementById("btnRefreshLessons")?.addEventListener("click", renderLessons);
  document.getElementById("btnDownloadPdf")?.addEventListener("click", downloadLessonPdf);
}

document.addEventListener("DOMContentLoaded", () => {
  requireLogin();
  applySystemSettings();
  loadStudentProfile();
  renderLessons();
  bindLessonEvents();
});
