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

async function loadHome() {
  try {
    const [assignmentsResp, overview] = await Promise.all([
      apiGet("/api/student/assignments"),
      apiGet("/api/student/overview")
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

    setText("weakSpot", overview.analysis?.weak_spot || "--");
    setText("studyState", overview.analysis?.study_state || "--");
    setText("studyTip", overview.analysis?.study_tip || "--");
  } catch {
    renderList("taskList", [], "task");
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
