const studentExamDict = {
  zh: {
    enterExam: "进入考试",
    startExam: "开始考试",
    startQuiz: "开始小测"
  },
  en: {
    enterExam: "Enter exam",
    startExam: "Start exam",
    startQuiz: "Start quiz"
  }
};
const i18n = window.I18N || null;
if (i18n) i18n.registerDict("studentExam", studentExamDict);

function getLocale() {
  return i18n ? i18n.getLocale() : (localStorage.getItem("locale") || "zh");
}

function t(key) {
  if (i18n) return i18n.t("studentExam", key, key);
  const locale = getLocale();
  return (studentExamDict[locale] && studentExamDict[locale][key]) || studentExamDict.zh[key] || key;
}

function bindExamEvents() {
  document.getElementById("btnExam")?.addEventListener("click", () => {
    alert(t("enterExam"));
  });
  document.getElementById("btnStartExam")?.addEventListener("click", () => {
    alert(t("startExam"));
  });
  document.getElementById("btnStartQuiz")?.addEventListener("click", () => {
    alert(t("startQuiz"));
  });
}

document.addEventListener("DOMContentLoaded", () => {
  requireLogin();
  applySystemSettings();
  loadStudentProfile();
  bindExamEvents();
});
