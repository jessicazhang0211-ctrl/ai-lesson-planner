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
    const kpiSubmission = document.getElementById("kpiSubmission");
    const kpiAvgAll = document.getElementById("kpiAvgAll");
    const kpiAvgWeek = document.getElementById("kpiAvgWeek");
    const kpiLatest = document.getElementById("kpiLatest");
    if (kpiSubmission) kpiSubmission.textContent = `${overview.submission_rate ?? 0}%`;
    if (kpiAvgAll) kpiAvgAll.textContent = overview.avg_score_all != null ? String(overview.avg_score_all) : "--";
    if (kpiAvgWeek) kpiAvgWeek.textContent = overview.avg_score_week != null ? String(overview.avg_score_week) : "--";
    if (kpiLatest) kpiLatest.textContent = overview.latest_score != null ? String(overview.latest_score) : "--";

    renderTrendChart(overview.trend || []);

    const weakSpot = document.getElementById("weakSpot");
    const studyState = document.getElementById("studyState");
    const studyTip = document.getElementById("studyTip");
    if (weakSpot) weakSpot.textContent = overview.analysis?.weak_spot || "--";
    if (studyState) studyState.textContent = overview.analysis?.study_state || "--";
    if (studyTip) studyTip.textContent = overview.analysis?.study_tip || "--";
  } catch {
    renderTrendChart([]);
    const weakSpot = document.getElementById("weakSpot");
    const studyState = document.getElementById("studyState");
    const studyTip = document.getElementById("studyTip");
    if (weakSpot) weakSpot.textContent = "--";
    if (studyState) studyState.textContent = "--";
    if (studyTip) studyTip.textContent = "--";
  }
}

function renderTrendChart(items) {
  const box = document.getElementById("scoreTrend");
  if (!box) return;
  if (!items.length) {
    box.innerHTML = `<div style="color:#8a8f98;font-size:12px;">(empty)</div>`;
    return;
  }

  const width = 640;
  const height = 220;
  const padding = 24;
  const maxScore = Math.max(...items.map(i => i.score ?? 0), 100);
  const minScore = Math.min(...items.map(i => i.score ?? 0), 0);
  const range = Math.max(1, maxScore - minScore);

  const stepX = (width - padding * 2) / Math.max(1, items.length - 1);
  const points = items.map((item, idx) => {
    const x = padding + stepX * idx;
    const y = height - padding - ((item.score - minScore) / range) * (height - padding * 2);
    return { x, y, label: item.label || "" };
  });

  const path = points.map((p, idx) => `${idx === 0 ? "M" : "L"}${p.x},${p.y}`).join(" ");
  const dots = points.map(p => `<circle cx="${p.x}" cy="${p.y}" r="4" />`).join("");
  const labels = points.map(p => `<text x="${p.x}" y="${height - 6}" text-anchor="middle">${p.label}</text>`).join("");

  box.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" class="trend-svg" role="img" aria-label="score trend">
      <path d="${path}" class="trend-line"></path>
      ${dots}
      ${labels}
    </svg>
  `;
}

document.addEventListener("DOMContentLoaded", () => {
  requireLogin();
  applySystemSettings();
  loadStudentProfile();
  renderScores();
});
