function renderScores() {
  const scores = [
    { title: "数学随堂测验", meta: "2026-03-05", value: "92" },
    { title: "英语单元练习", meta: "2026-03-03", value: "88" }
  ];
  const scoreBox = document.getElementById("scoreList");
  if (scoreBox) {
    scoreBox.innerHTML = scores.map(item => {
      return `
        <div class="score-item">
          <div>
            <div class="score-title">${item.title}</div>
            <div class="score-sub">${item.meta}</div>
          </div>
          <div class="score-value">${item.value}</div>
        </div>
      `;
    }).join("");
  }

  const weakSpot = document.getElementById("weakSpot");
  const studyState = document.getElementById("studyState");
  const studyTip = document.getElementById("studyTip");
  if (weakSpot) weakSpot.textContent = "分数比较 / 应用题";
  if (studyState) studyState.textContent = "保持稳定，继续巩固";
  if (studyTip) studyTip.textContent = "建议每天完成 10 题基础练习";
}

document.addEventListener("DOMContentLoaded", () => {
  requireLogin();
  applySystemSettings();
  loadStudentProfile();
  renderScores();
});
