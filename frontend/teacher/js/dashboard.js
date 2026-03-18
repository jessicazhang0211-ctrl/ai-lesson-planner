// API-backed analytics for 学情分析页面
(function () {
  const API_BASE = "http://127.0.0.1:5000";
  const dashboardDict = {
    zh: {
      dashboardTitle: "学情分析",
      dashboardSub: "班级整体表现、作业完成度与 Gemini 教学建议一览。",
      refresh: "刷新",
      export: "导出概览",
      kpiStudentsLabel: "在册学生",
      kpiSubmitLabel: "本周提交",
      kpiSubmitHint: "作业提交率",
      kpiAccuracyLabel: "平均正确率",
      kpiAccuracyHint: "近 7 天",
      kpiRiskLabel: "待处理",
      kpiRiskHint: "预警 / 异常",
      monthTrendTitle: "月趋势",
      weekTrendTitle: "周趋势",
      trendSub: "提交率 & 正确率",
      rewardTitle: "奖励名单",
      rewardSub: "提交率/正确率/进步表现",
      adviceTitle: "AI 教学建议（Gemini）",
      adviceSub: "聚焦薄弱课程与讲解强化策略",
      classOverviewTitle: "班级概览",
      classOverviewSub: "各班提交率与正确率",
      tableClass: "班级",
      tableStudents: "学生数",
      tableSubmit: "提交率",
      tableAccuracy: "正确率",
      tablePending: "待处理",
      noData: "暂无数据",
      submitRate: "提交率",
      accuracyRate: "正确率",
      noPraise: "暂无表扬",
      noAdvice: "暂无建议",
      praise: "表扬",
      all: "全部",
      loading: "加载中...",
      loadFailed: "加载失败",
      exportHint: "导出功能可接入后端生成 PDF/Excel，这里仅为示例。"
    },
    en: {
      dashboardTitle: "Learning Analytics",
      dashboardSub: "Overview of class performance, submissions, and Gemini teaching recommendations.",
      refresh: "Refresh",
      export: "Export Overview",
      kpiStudentsLabel: "Students Enrolled",
      kpiSubmitLabel: "Weekly Submission",
      kpiSubmitHint: "Homework submission rate",
      kpiAccuracyLabel: "Average Accuracy",
      kpiAccuracyHint: "Last 7 days",
      kpiRiskLabel: "Pending",
      kpiRiskHint: "Alerts / Exceptions",
      monthTrendTitle: "Monthly Trend",
      weekTrendTitle: "Weekly Trend",
      trendSub: "Submission & Accuracy",
      rewardTitle: "Reward List",
      rewardSub: "Submission / Accuracy / Progress",
      adviceTitle: "AI Teaching Advice (Gemini)",
      adviceSub: "Focus on weak topics and reinforcement strategy",
      classOverviewTitle: "Class Overview",
      classOverviewSub: "Submission and accuracy by class",
      tableClass: "Class",
      tableStudents: "Students",
      tableSubmit: "Submission",
      tableAccuracy: "Accuracy",
      tablePending: "Pending",
      noData: "No data",
      submitRate: "Submission",
      accuracyRate: "Accuracy",
      noPraise: "No praise yet",
      noAdvice: "No advice",
      praise: "Praise",
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
  const teacherAdviceList = document.getElementById('teacherAdviceList');
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
    teacherAdvice: [],
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

  function renderStaticTexts() {
    document.querySelectorAll('[data-i18n-page]').forEach((el) => {
      const key = (el.getAttribute('data-i18n-page') || '').trim();
      if (!key) return;
      el.textContent = t(key);
    });
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

    const clampPercent = (v) => {
      const n = Number(v);
      if (!Number.isFinite(n)) return 0;
      // Keep bars inside chart area and leave space for value labels.
      return Math.min(82, Math.max(0, Math.round(n)));
    };

    items.forEach((item) => {
      const group = document.createElement('div');
      group.className = 'chart-group';

      const submitPct = clampPercent(item.submit);
      const accPct = clampPercent(item.accuracy);

      const submitBar = document.createElement('div');
      submitBar.className = 'chart-bar submit';
      submitBar.style.height = `${submitPct}%`;
      const submitVal = document.createElement('div');
      submitVal.className = 'value';
      submitVal.textContent = `${submitPct}%`;
      submitBar.appendChild(submitVal);

      const accBar = document.createElement('div');
      accBar.className = 'chart-bar accuracy';
      accBar.style.height = `${accPct}%`;
      const accVal = document.createElement('div');
      accVal.className = 'value';
      accVal.textContent = `${accPct}%`;
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

  function renderTeacherAdvice() {
    if (!teacherAdviceList) return;
    teacherAdviceList.innerHTML = '';
    if (!state.teacherAdvice.length) {
      teacherAdviceList.innerHTML = `<div class="advice-item"><span class="advice-text">${t("noAdvice")}</span></div>`;
      return;
    }
    state.teacherAdvice.forEach((line, idx) => {
      const item = document.createElement('div');
      item.className = 'advice-item';
      item.innerHTML = `<span class="advice-index">${idx + 1}</span><span class="advice-text">${line}</span>`;
      teacherAdviceList.appendChild(item);
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
    renderStaticTexts();
    renderKpi();
    renderMonthTrendLine(monthTrendChart, state.monthly || []);
    renderTrend(weekTrendChart, state.weekly || []);
    renderPraises();
    renderTeacherAdvice();
    renderTabs();
    renderTable();
  }

  async function refresh() {
    if (monthTrendChart) monthTrendChart.innerHTML = `<div class="muted">${t("loading")}</div>`;
    if (weekTrendChart) weekTrendChart.innerHTML = `<div class="muted">${t("loading")}</div>`;
    if (praiseList) praiseList.innerHTML = '';
    if (teacherAdviceList) teacherAdviceList.innerHTML = '';
    classTable.innerHTML = '';
    classTabs.innerHTML = '';
    try {
      const lang = encodeURIComponent(getLocale());
      const data = await apiGet(`/api/class/overview?lang=${lang}`);
      state = {
        classData: data.classes || [],
        monthly: data.monthly || [],
        weekly: data.weekly || [],
        praises: data.praises || [],
        risks: data.risks || [],
        teacherAdvice: data.teacherAdvice || [],
        overview: data.overview || { students: 0, active: 0, submitRate: 0, accuracyAvg: 0, risk: 0 }
      };
      renderAll();
    } catch {
      if (monthTrendChart) monthTrendChart.innerHTML = `<div class="muted">${t("loadFailed")}</div>`;
      if (weekTrendChart) weekTrendChart.innerHTML = `<div class="muted">${t("loadFailed")}</div>`;
      if (praiseList) praiseList.innerHTML = `<div class="risk-item"><span class="risk-name">${t("loadFailed")}</span></div>`;
      if (teacherAdviceList) teacherAdviceList.innerHTML = `<div class="advice-item"><span class="advice-text">${t("loadFailed")}</span></div>`;
    }
  }

  btnRefresh?.addEventListener('click', refresh);
  btnExport?.addEventListener('click', () => {
    alert(t("exportHint"));
  });

  window.addEventListener("app:locale-changed", () => {
    // Advice text is generated server-side, so re-fetch with locale.
    refresh();
  });

  refresh();
})();
