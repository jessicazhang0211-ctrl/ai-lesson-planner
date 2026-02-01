const teacherDict = {
  zh: {
    dashboard: "学情分析",
    lesson: "教案生成",
    ppt: "PPT 生成",
    exercise: "习题设计",
    class: "班级管理",
    settings: "设置"
  },
  en: {
    dashboard: "Learning Analytics",
    lesson: "Lesson Planner",
    ppt: "PPT Generator",
    exercise: "Exercise Builder",
    class: "Class Management",
    settings: "Settings"
  }
};
function applyTeacherLang() {
  const lang = localStorage.getItem("locale") || "zh";
  const t = teacherDict[lang];

  // 侧边栏
  document.querySelector("[data-i18n='dashboard']").textContent = t.dashboard;
  document.querySelector("[data-i18n='lesson']").textContent = t.lesson;
  document.querySelector("[data-i18n='ppt']").textContent = t.ppt;
  document.querySelector("[data-i18n='exercise']").textContent = t.exercise;
  document.querySelector("[data-i18n='class']").textContent = t.class;
  document.querySelector("[data-i18n='settings']").textContent = t.settings;

  // 页面标题（如果有）
  const titleEl = document.querySelector("[data-i18n-page]");
  if (titleEl) titleEl.textContent = t.dashboard;
}


(function applySystemSettings() {
  // 语言
  const lang = localStorage.getItem("locale") || "zh";
  document.documentElement.lang = lang;

  // 字体大小
  const fontSize = localStorage.getItem("font_size") || "medium";
  document.documentElement.setAttribute("data-font", fontSize);
})();


// 登录校验：未登录不能进入教师端
(function checkLogin() {
  const user = localStorage.getItem("login_user");
  if (!user) {
    alert("请先登录");
    window.location.href = "../login.html";
  }
})();


function toggleSidebar() {
  document.getElementById("sidebar").classList.toggle("collapsed");
}

function toggleUserMenu() {
  const menu = document.getElementById("userMenu");
  menu.style.display = menu.style.display === "block" ? "none" : "block";
}

function goHome() {
  location.reload();
}

// 点击空白处关闭用户菜单
document.addEventListener("click", function (e) {
  const userMenu = document.getElementById("userMenu");
  const topbarRight = document.querySelector(".topbar-right");

  if (!topbarRight.contains(e.target)) {
    userMenu.style.display = "none";
  }
});
function loadUserInfo() {
  const user = JSON.parse(localStorage.getItem("login_user"));
  if (user && user.name) {
    document.querySelector(".username").innerText = user.name;
  }
}

function logout() {
  localStorage.removeItem("login_user");
  window.location.href = "../login.html";
}

loadUserInfo();
applyTeacherLang();
