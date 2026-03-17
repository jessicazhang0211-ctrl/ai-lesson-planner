// API-backed analytics for 学情分析页面
(function () {
  const API_BASE = "http://127.0.0.1:5000";
  const dashboardDict = {
    zh: {
      noData: "暂无数据",
      submitRate: "提交率",
      accuracyRate: "正确率",
      noPraise: "暂无表扬",
      noRisk: "暂无预警",
      praise: "表扬",
      highRisk: "高风险",
      watch: "关注",
      all: "全部",
      loading: "加载中...",
      loadFailed: "加载失败",
      exportHint: "导出功能可接入后端生成 PDF/Excel，这里仅为示例。"
    },
    en: {
      noData: "No data",
      submitRate: "Submission",
      accuracyRate: "Accuracy",
      noPraise: "No praise yet",
      noRisk: "No alerts",
      praise: "Praise",
      highRisk: "High Risk",
      watch: "Watch",
      all: "All",
      loading: "Loading...",
      loadFailed: "Load failed",
      exportHint: "Export can be connected to backend PDF/Excel generation. This is a demo prompt."
    }
  };
  const i18n = window.I18N || null;
  if (i18n) i18n.registerDict("teacherDashboard", dashboardDict);

  function getLocale() {
    return i18n ? i18n.getLocale() : (localStorage.getItem("locale") || "zh");
  }

  function t(key) {
    if (i18n) return i18n.t("teacherDashboard", key, key);
    const locale = getLocale();
    return (dashboardDict[locale] && dashboardDict[locale][key]) || dashboardDict.zh[key] || key;
  }
  const kpiStudents = document.getElementById('kpiStudents');
  const kpiActiveHint = document.getElementById('kpiActiveHint');
  const kpiSubmit = document.getElementById('kpiSubmit');
  const kpiAccuracy = document.getElementById('kpiAccuracy');
  const kpiRisk = document.getElementById('kpiRisk');
  const monthTrendChart = document.getElementById('monthTrendChart');
  const weekTrendChart = document.getElementById('weekTrendChart');
  const praiseList = document.getElementById('praiseList');
  const riskList = document.getElementById('riskList');
  const classTable = document.querySelector('#classTable tbody');
  const classTabs = document.getElementById('classTabs');
  const btnRefresh = document.getElementById('btnRefresh');
  const btnExport = document.getElementById('btnExport');

  let state = {
    classData: [],
    monthly: [],
    weekly: [],
    praises: [],
    risks: [],
    overview: { students: 0, active: 0, submitRate: 0, accuracyAvg: 0, risk: 0 }
  };

  function getToken() {
    return localStorage.getItem("auth_token") || "";
  }

  async function apiGet(path) {
    const token = getToken();
    const res = await fetch(`${API_BASE}${path}`, {
      headers: { "Authorization": `Bearer ${token}` }
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.code !== 0) throw new Error(data.message || "api error");
    return data.data || {};
  }

  function rate(part, total) {
    if (!total) return 0;
    return Math.round((part / total) * 100);
  }

  function renderKpi() {
    kpiStudents.textContent = state.overview.students;
    kpiActiveHint.textContent = `${state.overview.active} / ${state.overview.students}`;
    kpiSubmit.textContent = `${state.overview.submitRate}%`;
    kpiAccuracy.textContent = `${state.overview.accuracyAvg}%`;
    kpiRisk.textContent = state.overview.risk;
  }

  function renderMonthTrendLine(box, items) {
    if (!box) return;
    box.innerHTML = '';
    if (!items.length) {
      box.innerHTML = `<div class="muted">${t("noData")}</div>`;
      return;
    }
    const width = 720;
    const height = 220;
    const padding = 26;
    const maxScore = Math.max(...items.map(i => i.submit ?? 0), ...items.map(i => i.accuracy ?? 0), 100);
    const minScore = Math.min(...items.map(i => i.submit ?? 0), ...items.map(i => i.accuracy ?? 0), 0);
    const range = Math.max(1, maxScore - minScore);
    const stepX = (width - padding * 2) / Math.max(1, items.length - 1);

    const submitPoints = items.map((item, idx) => {
      const x = padding + stepX * idx;
      const y = height - padding - ((item.submit - minScore) / range) * (height - padding * 2);
      return { x, y, label: item.day || "" };
    });
    const accPoints = items.map((item, idx) => {
      const x = padding + stepX * idx;
      const y = height - padding - ((item.accuracy - minScore) / range) * (height - padding * 2);
      return { x, y, label: item.day || "" };
    });

    const submitPath = submitPoints.map((p, idx) => `${idx === 0 ? "M" : "L"}${p.x},${p.y}`).join(" ");
    const accPath = accPoints.map((p, idx) => `${idx === 0 ? "M" : "L"}${p.x},${p.y}`).join(" ");
    const submitDots = submitPoints.map((p, idx) => {
      const item = items[idx] || {};
      return `<circle class="trend-dot submit" cx="${p.x}" cy="${p.y}" r="3" data-type="submit" data-day="${item.day || ''}" data-value="${item.submit ?? 0}" />`;
    }).join("");
    const accDots = accPoints.map((p, idx) => {
      const item = items[idx] || {};
      return `<circle class="trend-dot accuracy" cx="${p.x}" cy="${p.y}" r="3" data-type="accuracy" data-day="${item.day || ''}" data-value="${item.accuracy ?? 0}" />`;
    }).join("");

    const labels = items.map((item, idx) => {
      if (idx % 5 !== 0 && idx !== items.length - 1) return "";
      const x = padding + stepX * idx;
      return `<text x="${x}" y="${height - 6}" text-anchor="middle">${item.day || ""}</text>`;
    }).join("");

    box.innerHTML = `
      <svg viewBox="0 0 ${width} ${height}" class="trend-svg" role="img" aria-label="monthly trend">
        <path d="${submitPath}" class="trend-line submit"></path>
        ${submitDots}
        <path d="${accPath}" class="trend-line accuracy"></path>
        ${accDots}
        ${labels}
      </svg>
    `;

    const tooltip = document.createElement("div");
    tooltip.className = "trend-tooltip";
    box.appendChild(tooltip);

    box.querySelectorAll(".trend-dot").forEach(dot => {
      dot.addEventListener("mouseenter", () => {
        const type = dot.getAttribute("data-type");
        const day = dot.getAttribute("data-day") || "";
        const value = dot.getAttribute("data-value") || "0";
        const label = type === "submit" ? t("submitRate") : t("accuracyRate");
        const boxRect = box.getBoundingClientRect();
        const dotRect = dot.getBoundingClientRect();
        const x = dotRect.left - boxRect.left + dotRect.width / 2;
        const y = dotRect.top - boxRect.top;
        const margin = 10;
        const maxX = box.clientWidth - margin;
        const minX = margin;
        tooltip.textContent = `${day} · ${label} ${value}%`;
        const clampedX = Math.min(maxX, Math.max(minX, x));
        tooltip.style.left = `${clampedX}px`;
        tooltip.classList.add("show");
        const tooltipHeight = tooltip.offsetHeight || 0;
        const desiredTop = y - tooltipHeight - 8;
        const clampedTop = Math.min(box.clientHeight - margin, Math.max(margin, desiredTop));
        tooltip.style.top = `${clampedTop}px`;
      });
      dot.addEventListener("mouseleave", () => {
        tooltip.classList.remove("show");
      });
    });
  }

  function renderPraises() {
    if (!praiseList) return;
    praiseList.innerHTML = '';
    if (!state.praises.length) {
      praiseList.innerHTML = `<div class="risk-item"><span class="risk-name">${t("noPraise")}</span></div>`;
      return;
    }
    state.praises.forEach((r) => {
      const item = document.createElement('div');
      item.className = 'risk-item';
      const main = document.createElement('div');
      main.className = 'risk-main';
      const name = document.createElement('div');
      name.className = 'risk-name';
      name.textContent = r.name;
      const meta = document.createElement('div');
      meta.className = 'risk-meta';
      meta.textContent = `${r.className} · ${t("submitRate")} ${r.submit}% · ${t("accuracyRate")} ${r.accuracy}%`;
      main.appendChild(name);
      main.appendChild(meta);
      const tag = document.createElement('div');
      tag.className = 'tag praise';
      tag.textContent = t("praise");
      item.appendChild(main);
      item.appendChild(tag);
      praiseList.appendChild(item);
    });
  }

  function renderTrend(box, items) {
    if (!box) return;
    box.innerHTML = '';
    if (!items.length) {
      box.innerHTML = `<div class="muted">${t("noData")}</div>`;
      return;
    }
    items.forEach((item) => {
      const group = document.createElement('div');
      group.className = 'chart-group';

      const submitBar = document.createElement('div');
      submitBar.className = 'chart-bar submit';
      submitBar.style.height = `${item.submit}%`;
      const submitVal = document.createElement('div');
      submitVal.className = 'value';
      submitVal.textContent = `${item.submit}%`;
      submitBar.appendChild(submitVal);

      const accBar = document.createElement('div');
      accBar.className = 'chart-bar accuracy';
      accBar.style.height = `${item.accuracy}%`;
      const accVal = document.createElement('div');
      accVal.className = 'value';
      accVal.textContent = `${item.accuracy}%`;
      accBar.appendChild(accVal);

      const label = document.createElement('div');
      label.className = 'label';
      label.textContent = item.day;

      group.appendChild(submitBar);
      group.appendChild(accBar);
      group.appendChild(label);
      box.appendChild(group);
    });
  }

  function renderRisks() {
    riskList.innerHTML = '';
    if (!state.risks.length) {
      riskList.innerHTML = `<div class="risk-item"><span class="risk-name">${t("noRisk")}</span></div>`;
      return;
    }
    state.risks.forEach((r) => {
      const item = document.createElement('div');
      item.className = 'risk-item';
      const main = document.createElement('div');
      main.className = 'risk-main';
      const name = document.createElement('div');
      name.className = 'risk-name';
      name.textContent = r.name;
      const meta = document.createElement('div');
      meta.className = 'risk-meta';
      meta.textContent = `${r.className} · ${t("submitRate")} ${r.submit}% · ${t("accuracyRate")} ${r.accuracy}%`;
      main.appendChild(name);
      main.appendChild(meta);
      const tag = document.createElement('div');
      tag.className = `tag ${r.tag}`;
      tag.textContent = r.tag === 'danger' ? t("highRisk") : t("watch");
      item.appendChild(main);
      item.appendChild(tag);
      riskList.appendChild(item);
    });
  }

  function renderTabs() {
    classTabs.innerHTML = '';
    const allBtn = makeTab(t("all"), true);
    classTabs.appendChild(allBtn);
    state.classData.forEach((c) => classTabs.appendChild(makeTab(c.name)));
  }

  function makeTab(label, active = false) {
    const btn = document.createElement('button');
    btn.textContent = label;
    if (active) btn.classList.add('active');
    btn.addEventListener('click', () => {
      Array.from(classTabs.querySelectorAll('button')).forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      renderTable(label === t("all") ? null : label);
    });
    return btn;
  }

  function renderTable(filterName = null) {
    classTable.innerHTML = '';
    const rows = filterName ? state.classData.filter((c) => c.name === filterName) : state.classData;
    rows.forEach((c) => {
      const tr = document.createElement('tr');
      const submitRate = rate(c.submitted, c.total);
      const accuracy = c.accuracy;
      const riskPill = c.risk > 3 ? 'red' : c.risk > 1 ? 'orange' : 'green';
      tr.innerHTML = `
        <td>${c.name}</td>
        <td>${c.total}</td>
        <td>${submitRate}%</td>
        <td>${accuracy}%</td>
        <td><span class="pill ${riskPill}">${c.risk}</span></td>
      `;
      classTable.appendChild(tr);
    });
  }

  function renderAll() {
    renderKpi();
    renderMonthTrendLine(monthTrendChart, state.monthly || []);
    renderTrend(weekTrendChart, state.weekly || []);
    renderPraises();
    renderRisks();
    renderTabs();
    renderTable();
  }

  async function refresh() {
    if (monthTrendChart) monthTrendChart.innerHTML = `<div class="muted">${t("loading")}</div>`;
    if (weekTrendChart) weekTrendChart.innerHTML = `<div class="muted">${t("loading")}</div>`;
    if (praiseList) praiseList.innerHTML = '';
    riskList.innerHTML = '';
    classTable.innerHTML = '';
    classTabs.innerHTML = '';
    try {
      const data = await apiGet('/api/class/overview');
      state = {
        classData: data.classes || [],
        monthly: data.monthly || [],
        weekly: data.weekly || [],
        praises: data.praises || [],
        risks: data.risks || [],
        overview: data.overview || { students: 0, active: 0, submitRate: 0, accuracyAvg: 0, risk: 0 }
      };
      renderAll();
    } catch {
      if (monthTrendChart) monthTrendChart.innerHTML = `<div class="muted">${t("loadFailed")}</div>`;
      if (weekTrendChart) weekTrendChart.innerHTML = `<div class="muted">${t("loadFailed")}</div>`;
      if (praiseList) praiseList.innerHTML = `<div class="risk-item"><span class="risk-name">${t("loadFailed")}</span></div>`;
      riskList.innerHTML = `<div class="risk-item"><span class="risk-name">${t("loadFailed")}</span></div>`;
    }
  }

  btnRefresh?.addEventListener('click', refresh);
  btnExport?.addEventListener('click', () => {
    alert(t("exportHint"));
  });

  window.addEventListener("app:locale-changed", () => {
    renderAll();
  });

  refresh();
})();
