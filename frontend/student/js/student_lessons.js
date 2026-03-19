let lessonCache = [];
let selectedLessonId = null;
let pdfFontLoaded = false;

const lessonPageDict = {
  zh: {
    pageTitle: "教案资源 · 学生端",
    heroTitle: "老师教案资源",
    heroSub: "查看老师发布的教案与学习资料。",
    btnRefresh: "刷新",
    listTitle: "教案列表",
    listSub: "点击查看详情",
    btnDownloadPdf: "下载 PDF",
    emptyHint: "选择左侧教案查看详情",
    defaultTitle: "教案",
    view: "查看",
    empty: "(空)",
    pdfFontError: "PDF 字体加载失败，中文会乱码。请用本地静态服务器打开前端后重试。\n例如：cd frontend && python -m http.server 8000"
  },
  en: {
    pageTitle: "Lesson Resources · Student",
    heroTitle: "Teacher Lesson Resources",
    heroSub: "Browse lesson plans and learning materials published by your teacher.",
    btnRefresh: "Refresh",
    listTitle: "Lesson List",
    listSub: "Click to view details",
    btnDownloadPdf: "Download PDF",
    emptyHint: "Select a lesson on the left to view details",
    defaultTitle: "Lesson Plan",
    view: "View",
    empty: "(empty)",
    pdfFontError: "PDF font loading failed. CJK text may be garbled. Please open frontend via a local HTTP server and try again.\nExample: cd frontend && python -m http.server 8000"
  }
};

const i18n = window.I18N || null;
if (i18n) i18n.registerDict("studentLessons", lessonPageDict);

const PDF_FONT_FAMILY = "SanJiZiHaiSongGBK";
const PDF_FONT_FILE_NORMAL = "SanJiZiHaiSongGBK-2.ttf";
const PDF_FONT_FILE_BOLD = "SanJiZiHaiSongGBK-2.ttf";
const PDF_FONT_URL_NORMAL = "../assets/fonts/SanJiZiHaiSongGBK-2.ttf";
const PDF_FONT_URL_BOLD = "../assets/fonts/SanJiZiHaiSongGBK-2.ttf";

function getLocale() {
  return i18n ? i18n.getLocale() : (localStorage.getItem("locale") || "zh");
}

function t(key) {
  if (i18n) return i18n.t("studentLessons", key, key);
  const locale = getLocale();
  return (lessonPageDict[locale] && lessonPageDict[locale][key]) || lessonPageDict.zh[key] || key;
}

function applyPageI18n() {
  if (i18n) i18n.applyDataI18n("studentLessons", document);
  document.title = t("pageTitle");
}

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
  const dict = lessonPageDict[locale] || lessonPageDict.zh;
  try {
    const lessons = await apiGet("/api/student/lessons");
    lessonCache = lessons || [];
    if (!lessonCache.length) {
      box.innerHTML = `<div style="color:#8a8f98;font-size:12px;">${dict.empty}</div>`;
      return;
    }
    box.innerHTML = lessonCache.map(item => {
      const meta = item.published_at || item.created_at || "";
      const active = selectedLessonId === item.id ? "active" : "";
      return `
        <div class="lesson-item ${active}">
          <div>
            <div class="lesson-title">${item.title || dict.defaultTitle}</div>
            <div class="lesson-sub">${meta}</div>
          </div>
          <button class="btn" data-id="${item.id}">${dict.view}</button>
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
    box.innerHTML = `<div style="color:#8a8f98;font-size:12px;">${dict.empty}</div>`;
  }
}

function openLesson(id) {
  const title = document.getElementById("lessonTitle");
  const content = document.getElementById("lessonContent");
  const meta = document.getElementById("lessonMeta");
  const empty = document.getElementById("lessonEmpty");
  if (!title || !content || !meta || !empty) return;
  const locale = getLocale();
  const dict = lessonPageDict[locale] || lessonPageDict.zh;
  const item = lessonCache.find(x => x.id === id);
  if (!item) return;
  selectedLessonId = id;
  title.textContent = item.title || dict.defaultTitle;
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
    const dict = lessonPageDict[locale] || lessonPageDict.zh;
    alert(dict.pdfFontError);
    return;
  }
  const locale = getLocale();
  const dict = lessonPageDict[locale] || lessonPageDict.zh;
  const title = item.title || dict.defaultTitle;
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
  applyPageI18n();
  renderLessons();
  bindLessonEvents();
  if (i18n) {
    i18n.onLocaleChange(() => {
      applyPageI18n();
      renderLessons();
    });
  }
});
