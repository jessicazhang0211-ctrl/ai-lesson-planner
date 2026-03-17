const scoresDict = {
  zh: {
    empty: "(空)",
    loading: "加载中...",
    exercise: "练习",
    homework: "作业"
  },
  en: {
    empty: "(empty)",
    loading: "Loading...",
    exercise: "Exercise",
    homework: "Assignment"
  }
};
const i18n = window.I18N || null;
if (i18n) i18n.registerDict("studentScores", scoresDict);

function getLocale() {
  return i18n ? i18n.getLocale() : (localStorage.getItem("locale") || "zh");
}

function t(key) {
  if (i18n) return i18n.t("studentScores", key, key);
  const locale = getLocale();
  return (scoresDict[locale] && scoresDict[locale][key]) || scoresDict.zh[key] || key;
}

async function renderScores() {
  const scoreBox = document.getElementById("scoreList");
  if (scoreBox) {
    try {
      const scores = await apiGet("/api/student/scores");
      if (!scores.length) {
        scoreBox.innerHTML = `<div style="color:#8a8f98;font-size:12px;">${t("empty")}</div>`;
      } else {
        scoreBox.innerHTML = scores.map(item => {
          const value = item.score != null ? item.score : "--";
          const maxScore = item.max_score != null ? item.max_score : null;
          const display = maxScore != null ? `${value}/${maxScore}` : `${value}`;
          const meta = item.completed_at || item.published_at || "";
          return `
            <div class="score-item">
              <div>
                <div class="score-title">${item.title || t("exercise")}</div>
                <div class="score-sub">${meta}</div>
              </div>
              <div class="score-value">${display}</div>
            </div>
          `;
        }).join("");
      }
    } catch {
      scoreBox.innerHTML = `<div style="color:#8a8f98;font-size:12px;">${t("empty")}</div>`;
    }
  }

  try {
    const trendBox = document.getElementById("scoreTrend");
    if (trendBox) trendBox.innerHTML = `<div class="loading">${t("loading")}</div>`;
    const overview = await apiGet("/api/student/overview");
    const kpiSubmission = document.getElementById("kpiSubmission");
    const kpiAvgAll = document.getElementById("kpiAvgAll");
    const kpiAvgWeek = document.getElementById("kpiAvgWeek");
    const kpiLatest = document.getElementById("kpiLatest");
    if (kpiSubmission) kpiSubmission.textContent = `${overview.submission_rate ?? 0}%`;
    if (kpiAvgAll) kpiAvgAll.textContent = overview.avg_score_all != null ? String(overview.avg_score_all) : "--";
    if (kpiAvgWeek) kpiAvgWeek.textContent = overview.avg_score_week != null ? String(overview.avg_score_week) : "--";
    if (kpiLatest) {
      const latest = overview.latest_score != null ? String(overview.latest_score) : "--";
      const latestTotal = overview.latest_total_score != null ? String(overview.latest_total_score) : null;
      kpiLatest.textContent = latestTotal ? `${latest}/${latestTotal}` : latest;
    }

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

function escapeAttr(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll("\"", "&quot;");
}

function renderTrendChart(items) {
  const box = document.getElementById("scoreTrend");
  if (!box) return;
  if (!items.length) {
    box.innerHTML = `<div style="color:#8a8f98;font-size:12px;">${t("empty")}</div>`;
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
  const dots = points.map((p, idx) => {
    const item = items[idx] || {};
    const score = item.score != null ? item.score : "--";
    const title = escapeAttr(item.title || "");
    const label = escapeAttr(item.label || "");
    return `<circle class="trend-point" cx="${p.x}" cy="${p.y}" r="4" data-score="${score}" data-title="${title}" data-label="${label}" />`;
  }).join("");
  const labels = points.map(p => `<text x="${p.x}" y="${height - 6}" text-anchor="middle">${p.label}</text>`).join("");

  box.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" class="trend-svg" role="img" aria-label="score trend">
      <path d="${path}" class="trend-line"></path>
      ${dots}
      ${labels}
    </svg>
  `;

  const tooltip = document.createElement("div");
  tooltip.className = "trend-tooltip";
  tooltip.id = "trendTooltip";
  box.appendChild(tooltip);

  box.querySelectorAll(".trend-point").forEach(point => {
    point.addEventListener("mousemove", (e) => {
      const score = point.getAttribute("data-score") || "--";
      const title = point.getAttribute("data-title") || "";
      const label = point.getAttribute("data-label") || "";
      const rect = box.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      tooltip.textContent = `${title || t("homework")}: ${score}${label ? ` · ${label}` : ""}`;
      tooltip.style.left = `${x}px`;
      tooltip.style.top = `${y - 12}px`;
      tooltip.classList.add("show");
    });
    point.addEventListener("mouseleave", () => {
      tooltip.classList.remove("show");
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  requireLogin();
  applySystemSettings();
  loadStudentProfile();
  renderScores();
});
