// Simple mocked analytics for 学情分析页面
(function () {
  const kpiStudents = document.getElementById('kpiStudents');
  const kpiActiveHint = document.getElementById('kpiActiveHint');
  const kpiSubmit = document.getElementById('kpiSubmit');
  const kpiAccuracy = document.getElementById('kpiAccuracy');
  const kpiRisk = document.getElementById('kpiRisk');
  const trendChart = document.getElementById('trendChart');
  const riskList = document.getElementById('riskList');
  const classTable = document.querySelector('#classTable tbody');
  const classTabs = document.getElementById('classTabs');
  const btnRefresh = document.getElementById('btnRefresh');
  const btnExport = document.getElementById('btnExport');

  let state = buildMock();

  function buildMock() {
    const classes = ['高一(1)班', '高一(2)班', '高一(3)班'];
    const classData = classes.map((name) => {
      const total = rand(32, 45);
      const submitted = rand(Math.floor(total * 0.6), total);
      const accuracy = rand(70, 96);
      const risk = rand(0, 4);
      return {
        name,
        total,
        submitted,
        accuracy,
        risk,
      };
    });

    const weekly = Array.from({ length: 7 }, (_, i) => ({
      day: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][i],
      submit: rand(62, 95),
      accuracy: rand(68, 97),
    }));

    const risks = Array.from({ length: rand(2, 6) }).map(() => {
      const score = rand(45, 70);
      const submit = rand(40, 80);
      const flag = score < 55 || submit < 60 ? 'danger' : 'warn';
      return {
        name: randomName(),
        className: classes[rand(0, classes.length - 1)],
        submit,
        accuracy: score,
        tag: flag,
      };
    });

    const totals = classData.reduce(
      (acc, cur) => {
        acc.total += cur.total;
        acc.submitted += cur.submitted;
        acc.risk += cur.risk;
        acc.accuracySum += cur.accuracy;
        return acc;
      },
      { total: 0, submitted: 0, risk: 0, accuracySum: 0 }
    );

    const active = rand(Math.floor(totals.total * 0.7), totals.total);

    return {
      classData,
      weekly,
      risks,
      overview: {
        students: totals.total,
        active,
        submitRate: rate(totals.submitted, totals.total),
        accuracyAvg: Math.round(totals.accuracySum / classData.length),
        risk: totals.risk + risks.length,
      },
    };
  }

  function rate(part, total) {
    if (!total) return 0;
    return Math.round((part / total) * 100);
  }

  function rand(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
  }

  function randomName() {
    const last = ['张', '李', '王', '赵', '刘', '陈', '杨'];
    const first = ['晨', '琪', '然', '悦', '宇', '凯', '欣', '婷'];
    return last[rand(0, last.length - 1)] + first[rand(0, first.length - 1)];
  }

  function renderKpi() {
    kpiStudents.textContent = state.overview.students;
    kpiActiveHint.textContent = `${state.overview.active} / ${state.overview.students}`;
    kpiSubmit.textContent = `${state.overview.submitRate}%`;
    kpiAccuracy.textContent = `${state.overview.accuracyAvg}%`;
    kpiRisk.textContent = state.overview.risk;
  }

  function renderTrend() {
    trendChart.innerHTML = '';
    state.weekly.forEach((item) => {
      const bar = document.createElement('div');
      bar.className = 'chart-bar';
      bar.style.height = `${item.submit}%`;
      const val = document.createElement('div');
      val.className = 'value';
      val.textContent = `${item.submit}%`;
      const label = document.createElement('div');
      label.className = 'label';
      label.textContent = item.day;
      bar.appendChild(val);
      bar.appendChild(label);
      trendChart.appendChild(bar);
    });
  }

  function renderRisks() {
    riskList.innerHTML = '';
    if (!state.risks.length) {
      riskList.innerHTML = '<div class="risk-item"><span class="risk-name">暂无预警</span></div>';
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
      meta.textContent = `${r.className} · 提交率 ${r.submit}% · 正确率 ${r.accuracy}%`;
      main.appendChild(name);
      main.appendChild(meta);
      const tag = document.createElement('div');
      tag.className = `tag ${r.tag}`;
      tag.textContent = r.tag === 'danger' ? '高风险' : '关注';
      item.appendChild(main);
      item.appendChild(tag);
      riskList.appendChild(item);
    });
  }

  function renderTabs() {
    classTabs.innerHTML = '';
    const allBtn = makeTab('全部', true);
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
      renderTable(label === '全部' ? null : label);
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
    renderTrend();
    renderRisks();
    renderTabs();
    renderTable();
  }

  function refresh() {
    state = buildMock();
    renderAll();
  }

  btnRefresh?.addEventListener('click', refresh);
  btnExport?.addEventListener('click', () => {
    alert('导出功能可接入后端生成 PDF/Excel，这里仅为示例。');
  });

  renderAll();
})();
