let lessonCache = [];
let selectedLessonId = null;
let pdfFontLoaded = false;
const lessonPageDict = {
  zh: {
    defaultTitle: "教案",
    view: "查看",
    empty: "(空)",
    pdfFontError: "PDF 字体加载失败，中文会乱码。请用本地静态服务器打开前端后重试。\n例如：cd frontend && python -m http.server 8000"
  },
  en: {
    defaultTitle: "Lesson Plan",
    view: "View",
    empty: "(empty)",
    pdfFontError: "PDF font loading failed. CJK text may be garbled. Please open frontend via a local HTTP server and try again.\nExample: cd frontend && python -m http.server 8000"
  }
};
const PDF_FONT_FAMILY = "SanJiZiHaiSongGBK";
const PDF_FONT_FILE_NORMAL = "SanJiZiHaiSongGBK-2.ttf";
const PDF_FONT_FILE_BOLD = "SanJiZiHaiSongGBK-2.ttf";
const PDF_FONT_URL_NORMAL = "../assets/fonts/SanJiZiHaiSongGBK-2.ttf";
const PDF_FONT_URL_BOLD = "../assets/fonts/SanJiZiHaiSongGBK-2.ttf";

function getFontCandidates(url) {
  const baseName = "SanJiZiHaiSongGBK-2.ttf";
  return [
    url,
    `../assets/fonts/${baseName}`,
    `/assets/fonts/${baseName}`,
    `/frontend/assets/fonts/${baseName}`
  ];
}

async function ensurePdfFontLoaded(doc) {
  if (pdfFontLoaded) return;
  const loadFontFile = async (url) => {
    const res = await fetch(url);
    if (!res.ok) throw new Error("font load failed");
    const buffer = await res.arrayBuffer();
    const bytes = new Uint8Array(buffer);
    let binary = "";
    for (let i = 0; i < bytes.length; i += 1) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  };

  const loadByCandidates = async (candidates) => {
    let lastError = null;
    for (const u of candidates) {
      try {
        return await loadFontFile(u);
      } catch (e) {
        lastError = e;
      }
    }
    throw lastError || new Error("font load failed");
  };

  const normalBase64 = await loadByCandidates(getFontCandidates(PDF_FONT_URL_NORMAL));
  const boldBase64 = await loadByCandidates(getFontCandidates(PDF_FONT_URL_BOLD));
  doc.addFileToVFS(PDF_FONT_FILE_NORMAL, normalBase64);
  doc.addFileToVFS(PDF_FONT_FILE_BOLD, boldBase64);
  doc.addFont(PDF_FONT_FILE_NORMAL, PDF_FONT_FAMILY, "normal");
  doc.addFont(PDF_FONT_FILE_BOLD, PDF_FONT_FAMILY, "bold");
  pdfFontLoaded = true;
}

async function renderLessons() {
  const box = document.getElementById("lessonList");
  if (!box) return;
  const locale = getLocale();
  const t = lessonPageDict[locale] || lessonPageDict.zh;
  try {
    const lessons = await apiGet("/api/student/lessons");
    lessonCache = lessons || [];
    if (!lessonCache.length) {
      box.innerHTML = `<div style="color:#8a8f98;font-size:12px;">${t.empty}</div>`;
      return;
    }
    box.innerHTML = lessonCache.map(item => {
      const meta = item.published_at || item.created_at || "";
      const active = selectedLessonId === item.id ? "active" : "";
      return `
        <div class="lesson-item ${active}">
          <div>
            <div class="lesson-title">${item.title || t.defaultTitle}</div>
            <div class="lesson-sub">${meta}</div>
          </div>
          <button class="btn" data-id="${item.id}">${t.view}</button>
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
    box.innerHTML = `<div style="color:#8a8f98;font-size:12px;">${t.empty}</div>`;
  }
}

function openLesson(id) {
  const title = document.getElementById("lessonTitle");
  const content = document.getElementById("lessonContent");
  const meta = document.getElementById("lessonMeta");
  const empty = document.getElementById("lessonEmpty");
  if (!title || !content || !meta || !empty) return;
  const locale = getLocale();
  const t = lessonPageDict[locale] || lessonPageDict.zh;
  const item = lessonCache.find(x => x.id === id);
  if (!item) return;
  selectedLessonId = id;
  title.textContent = item.title || t.defaultTitle;
  content.textContent = item.content || "";
  meta.textContent = item.published_at || item.created_at || "";
  empty.style.display = item.content ? "none" : "flex";
  renderLessons();
}

async function downloadLessonPdf() {
  const item = lessonCache.find(x => x.id === selectedLessonId);
  if (!item) return;
  const jspdf = window.jspdf;
  if (!jspdf || !jspdf.jsPDF) return;
  const doc = new jspdf.jsPDF({ unit: "pt", format: "a4" });
  try {
    await ensurePdfFontLoaded(doc);
    doc.setFont(PDF_FONT_FAMILY, "normal");
  } catch {
    const locale = getLocale();
    const t = lessonPageDict[locale] || lessonPageDict.zh;
    alert(t.pdfFontError);
    return;
  }
  const locale = getLocale();
  const t = lessonPageDict[locale] || lessonPageDict.zh;
  const title = item.title || t.defaultTitle;
  const content = item.content || "";
  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const marginX = 40;
  const marginTop = 48;
  const lineHeight = 16;
  doc.setFont(doc.getFont().fontName, "bold");
  doc.setFontSize(16);
  doc.text(title, marginX, marginTop);
  doc.setFont(doc.getFont().fontName, "normal");
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
