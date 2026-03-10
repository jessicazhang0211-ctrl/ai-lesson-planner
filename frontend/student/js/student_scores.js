async function renderScores() {
  const scoreBox = document.getElementById("scoreList");
  if (scoreBox) {
    try {
      const scores = await apiGet("/api/student/scores");
      if (!scores.length) {
        scoreBox.innerHTML = `<div style="color:#8a8f98;font-size:12px;">(empty)</div>`;
      } else {
        scoreBox.innerHTML = scores.map(item => {
          const value = item.score != null ? item.score : "--";
          const meta = item.completed_at || item.published_at || "";
          return `
            <div class="score-item">
              <div>
                <div class="score-title">${item.title || "练习"}</div>
                <div class="score-sub">${meta}</div>
              </div>
              <div class="score-value">${value}</div>
            </div>
          `;
        }).join("");
      }
    } catch {
      scoreBox.innerHTML = `<div style="color:#8a8f98;font-size:12px;">(empty)</div>`;
    }
  }

  try {
    const overview = await apiGet("/api/student/overview");
    const weakSpot = document.getElementById("weakSpot");
    const studyState = document.getElementById("studyState");
    const studyTip = document.getElementById("studyTip");
    if (weakSpot) weakSpot.textContent = overview.analysis?.weak_spot || "--";
    if (studyState) studyState.textContent = overview.analysis?.study_state || "--";
    if (studyTip) studyTip.textContent = overview.analysis?.study_tip || "--";
  } catch {
    const weakSpot = document.getElementById("weakSpot");
    const studyState = document.getElementById("studyState");
    const studyTip = document.getElementById("studyTip");
    if (weakSpot) weakSpot.textContent = "--";
    if (studyState) studyState.textContent = "--";
    if (studyTip) studyTip.textContent = "--";
  }
}

document.addEventListener("DOMContentLoaded", () => {
  requireLogin();
  applySystemSettings();
  loadStudentProfile();
  renderScores();
});
