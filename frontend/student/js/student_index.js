const studentHomeDict = {
  zh: {
    pageTitle: "学生端 · AI 辅助备课系统",
    heroTitle: "你的学习仪表盘",
    heroSub: "待办任务和个人学情分析集中展示。",
    btnQuickPractice: "开始练习",
    btnQuickReview: "开始复习",
    kpiTodoLabel: "待完成作业",
    kpiTodoSub: "来自老师发布",
    kpiPracticeLabel: "本周练习",
    kpiPracticeSub: "已完成题数",
    kpiAccuracyLabel: "平均正确率",
    kpiAccuracySub: "最近 7 天",
    kpiExamLabel: "最近考试",
    kpiExamSub: "最新成绩",
    taskTitle: "待办任务",
    taskSub: "老师发布的练习题与作业",
    btnRefresh: "刷新",
    analysisTitle: "个人学情分析",
    analysisSub: "学习趋势与薄弱点提醒",
    weakSpotLabel: "薄弱知识点",
    studyStateLabel: "学习状态",
    studyTipLabel: "建议",
    errorDistLabel: "错因分布",
    empty: "(空)",
    start: "开始",
    exercise: "练习",
    completed: "已完成",
    pending: "待完成"
  },
  en: {
    pageTitle: "Student Dashboard · AI Lesson Planner",
    heroTitle: "Your Learning Dashboard",
    heroSub: "Centralized view of tasks and personal learning insights.",
    btnQuickPractice: "Start Practice",
    btnQuickReview: "Start Review",
    kpiTodoLabel: "Pending Assignments",
    kpiTodoSub: "Published by your teacher",
    kpiPracticeLabel: "Practice This Week",
    kpiPracticeSub: "Questions completed",
    kpiAccuracyLabel: "Average Accuracy",
    kpiAccuracySub: "Last 7 days",
    kpiExamLabel: "Latest Exam",
    kpiExamSub: "Most recent score",
    taskTitle: "To-do Tasks",
    taskSub: "Exercises and assignments from your teacher",
    btnRefresh: "Refresh",
    analysisTitle: "Learning Insights",
    analysisSub: "Learning trend and weak-point reminders",
    weakSpotLabel: "Weak Knowledge Point",
    studyStateLabel: "Study Status",
    studyTipLabel: "Suggestion",
    errorDistLabel: "Error Type Distribution",
    empty: "(empty)",
    start: "Start",
    exercise: "Exercise",
    completed: "Completed",
    pending: "Pending"
  }
};
const i18n = window.I18N || null;
if (i18n) i18n.registerDict("studentHome", studentHomeDict);

function getLocale() {
  return i18n ? i18n.getLocale() : (localStorage.getItem("locale") || "zh");
}

function t(key) {
  if (i18n) return i18n.t("studentHome", key, key);
  const locale = getLocale();
  return (studentHomeDict[locale] && studentHomeDict[locale][key]) || studentHomeDict.zh[key] || key;
}

function translateInsightValue(value, key) {
  const raw = String(value || "").trim();
  if (!raw || getLocale() !== "en") return raw;

  const commonMap = {
    "--": "--",
    "薄弱知识点": "Weak knowledge point",
    "学习状态": "Study status",
    "建议": "Suggestion",
    "基础薄弱": "Needs fundamentals reinforcement",
    "良好": "Good",
    "稳定": "Stable",
    "波动": "Fluctuating",
    "需提升": "Needs improvement",
    "继续保持": "Keep it up",
    "重点复习": "Focus on review",
    "暂无明显薄弱点": "No obvious weak point yet",
    "数据不足": "Insufficient data",
    "表现优秀": "Excellent performance",
    "稳定提升": "Steady improvement",
    "需要加强": "Needs reinforcement",
    "完成更多作业后再进行分析": "Complete more assignments for a more reliable analysis",
    "保持节奏，尝试提高综合题": "Keep the pace and challenge more comprehensive questions",
    "建议巩固错题题型": "Focus on consolidating question types you often get wrong",
    "优先补齐基础题型": "Prioritize strengthening foundational question types"
  };
  if (Object.prototype.hasOwnProperty.call(commonMap, raw)) return commonMap[raw];

  const weakRateMatch = raw.match(/^(单选|多选|判断|填空|简答|其他)题错误率偏高$/);
  if (weakRateMatch) {
    const typeMap = {
      "单选": "single-choice",
      "多选": "multiple-choice",
      "判断": "true/false",
      "填空": "fill-in-the-blank",
      "简答": "short-answer",
      "其他": "other"
    };
    const qType = typeMap[weakRateMatch[1]] || "specific";
    return `High error rate in ${qType} questions`;
  }

  const weakSpotMap = {
    "分数比较": "Fraction comparison",
    "分数计算": "Fraction operations",
    "应用题": "Word problems",
    "几何": "Geometry",
    "口算": "Mental arithmetic"
  };
  if (key === "weak_spot" && Object.prototype.hasOwnProperty.call(weakSpotMap, raw)) {
    return weakSpotMap[raw];
  }

  return raw;
}

function applyPageI18n() {
  if (i18n) i18n.applyDataI18n("studentHome", document);
  document.title = t("pageTitle");
}

function renderList(id, items, type) {
  const box = document.getElementById(id);
  if (!box) return;
  if (!items.length) {
    box.innerHTML = `<div style="color:#8a8f98;font-size:12px;">${t("empty")}</div>`;
    return;
  }
  box.innerHTML = items.map(item => {
    if (type === "task") {
      return `
        <div class="task-item">
          <div>
            <div class="task-title">${item.title}</div>
            <div class="task-meta">${item.meta}</div>
          </div>
          <button class="btn">${t("start")}</button>
        </div>
      `;
    }
    return "";
  }).join("");
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function renderErrorDistribution(stats) {
  const box = document.getElementById("errorDistChart");
  if (!box) return;
  const map = (stats && typeof stats === "object") ? stats : {};
  const keys = ["概念", "计算", "审题"];
  const labels = getLocale() === "en"
    ? { "概念": "Concept", "计算": "Computation", "审题": "Reading" }
    : { "概念": "概念", "计算": "计算", "审题": "审题" };
  const total = keys.reduce((s, k) => s + Number(map[k] || 0), 0);
  if (!total) {
    box.textContent = "--";
    return;
  }

  box.innerHTML = keys.map((k) => {
    const n = Number(map[k] || 0);
    const pct = Math.round((n / total) * 100);
    return `
      <div style="margin:6px 0;">
        <div style="display:flex;justify-content:space-between;font-size:12px;color:#666;">
          <span>${labels[k]}</span><span>${pct}%</span>
        </div>
        <div style="height:8px;background:#eef0f3;border-radius:999px;overflow:hidden;">
          <div style="height:100%;width:${pct}%;background:#056de8;"></div>
        </div>
      </div>
    `;
  }).join("");
}

async function loadHome() {
  try {
    const locale = getLocale();
    const [assignmentsResp, overview] = await Promise.all([
      apiGet("/api/student/assignments"),
      apiGet(`/api/student/overview?lang=${encodeURIComponent(locale)}`)
    ]);
    const assignments = normalizeAssignments(assignmentsResp);

    const tasks = (assignments || [])
      .filter(a => a.resource_type === "exercise")
      .filter(a => a.status !== "completed")
      .map(a => ({
        title: a.title || t("exercise"),
        meta: `${a.status === "completed" ? t("completed") : t("pending")} · ${a.created_at || ""}`
      }));

    renderList("taskList", tasks, "task");

    setText("kpiTodo", String(overview.todo ?? 0));
    setText("kpiPractice", String(overview.completed ?? 0));
    setText("kpiAccuracy", overview.avg_score != null ? `${overview.avg_score}%` : "--");
    setText("kpiExam", overview.latest_score != null ? String(overview.latest_score) : "--");

    setText("weakSpot", translateInsightValue(overview.analysis?.weak_spot || "--", "weak_spot") || "--");
    setText("studyState", translateInsightValue(overview.analysis?.study_state || "--", "study_state") || "--");
    setText("studyTip", translateInsightValue(overview.analysis?.study_tip || "--", "study_tip") || "--");
    renderErrorDistribution(overview.student_profile?.error_type_stats || {});
  } catch {
    renderList("taskList", [], "task");
    renderErrorDistribution({});
  }
}

function bindHomeEvents() {
  document.getElementById("btnQuickPractice")?.addEventListener("click", () => {
    window.location.href = "./practice.html";
  });
  document.getElementById("btnQuickExam")?.addEventListener("click", () => {
    window.location.href = "./review.html";
  });
  document.getElementById("btnRefreshTasks")?.addEventListener("click", loadHome);
}

document.addEventListener("DOMContentLoaded", () => {
  requireLogin();
  applySystemSettings();
  loadStudentProfile();
  applyPageI18n();
  loadHome();
  bindHomeEvents();
  if (i18n) {
    i18n.onLocaleChange(() => {
      applyPageI18n();
      loadHome();
    });
  }
});
