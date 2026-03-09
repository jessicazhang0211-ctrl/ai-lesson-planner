function bindExamEvents() {
  document.getElementById("btnExam")?.addEventListener("click", () => {
    alert("进入考试");
  });
  document.getElementById("btnStartExam")?.addEventListener("click", () => {
    alert("开始考试");
  });
  document.getElementById("btnStartQuiz")?.addEventListener("click", () => {
    alert("开始小测");
  });
}

document.addEventListener("DOMContentLoaded", () => {
  requireLogin();
  applySystemSettings();
  loadStudentProfile();
  bindExamEvents();
});
