// ========== 跳转到个人信息 ========== 
function goProfile() {
  window.location.href = "./profile.html";
}

// ========== 跳转到班级信息 ========== 
function goClassInfo() {
  window.location.href = "./class.html";
}

// ========== 跳转到设置 ========== 
function goSettings() {
  window.location.href = "./settings.html";
}
// ========== i18n 字典 ==========
const teacherDict = {
  zh: {
    appName: "AI 辅助备课系统",
    dashboard: "学情分析",
    lesson: "教案生成",
    ppt: "PPT 生成",
    exercise: "习题设计",
    resource: "资源管理",
    review: "作业批改",
    class: "班级管理",
    settings: "设置",
    loginFirst: "请先登录",
    profile: "个人信息",
    classInfo: "班级信息",
    logout: "退出登录",
  },
  en: {
    appName: "AI Lesson Planner",
    dashboard: "Learning Analytics",
    lesson: "Lesson Planner",
    ppt: "PPT Generator",
    exercise: "Exercise Builder",
    resource: "Resource Manager",
    review: "Review",
    class: "Class Management",
    settings: "Settings",
    loginFirst: "Please sign in first",
    profile: "Profile",
    classInfo: "Class Info",
    logout: "Sign out",
  }
};

function getLocale() {
  return localStorage.getItem("locale") || "zh";
}

// 安全赋值（避免元素不存在时报错）
function setText(selector, text) {
  document.querySelectorAll(selector).forEach((el) => {
    el.textContent = text;
  });
}

// ========== 应用系统设置：语言 + 字体 ==========
function applySystemSettings() {
  const lang = getLocale();
  document.documentElement.lang = lang === "zh" ? "zh-CN" : "en";

  const fontSize = localStorage.getItem("font_size") || "medium";
  document.documentElement.setAttribute("data-font", fontSize);
}

// ========== 应用教师端语言 ==========
function applyTeacherLang() {
  const lang = getLocale();
  const t = teacherDict[lang];

  // 顶部系统名（如果 settings.html/index.html 都有 appName 元素）
  setText("#appName", t.appName);

  // 侧边栏（注意：settings.html 里用的是 <a>，textContent 也一样）
  setText("[data-i18n='dashboard']", t.dashboard);
  setText("[data-i18n='lesson']", t.lesson);
  setText("[data-i18n='ppt']", t.ppt);
  setText("[data-i18n='exercise']", t.exercise);
  setText("[data-i18n='resource']", t.resource);
  setText("[data-i18n='review']", t.review);
  setText("[data-i18n='class']", t.class);
  setText("[data-i18n='settings']", t.settings);
  setText("[data-i18n='profile']", t.profile);
  setText("[data-i18n='classInfo']", t.classInfo);
  setText("[data-i18n='logout']", t.logout);

  // 仅处理未指定 key 的页面标题，避免覆盖各页面自有 i18n-page 逻辑
  document.querySelectorAll("[data-i18n-page]").forEach((el) => {
    const key = (el.getAttribute("data-i18n-page") || "").trim();
    if (!key || key === "dashboard") {
      el.textContent = t.dashboard;
    }
  });
}

// ========== 登录校验：未登录不能进入教师端 ==========
(function checkLogin() {
  const token = localStorage.getItem("auth_token");
  if (!token) {
    alert(teacherDict[getLocale()].loginFirst);
    window.location.href = "../login.html";
  }
})();

// ========== 侧边栏折叠 ==========
function toggleSidebar() {
  const sidebar = document.getElementById("sidebar");
  if (sidebar) sidebar.classList.toggle("collapsed");
}

// ========== 用户菜单 ==========
function toggleUserMenu() {
  const menu = document.getElementById("userMenu");
  if (!menu) return;
  menu.style.display = menu.style.display === "block" ? "none" : "block";
}

// 点击空白处关闭用户菜单（如果页面有 topbar-right）
document.addEventListener("click", function (e) {
  const userMenu = document.getElementById("userMenu");
  const topbarRight = document.querySelector(".topbar-right");
  if (!userMenu || !topbarRight) return;

  if (!topbarRight.contains(e.target)) {
    userMenu.style.display = "none";
  }
});

// ========== 点击 logo 回主页 ==========
function goHome() {
  // ✅ 不用 reload：无论在 settings.html 还是其它页都回主页
  window.location.href = "./index.html";
}

// ========== 载入用户信息 ==========
function loadUserInfo() {
  const raw = localStorage.getItem("login_user");
  if (!raw) return;
  const user = JSON.parse(raw);

  const nameEl = document.querySelector(".username");
  if (nameEl) nameEl.textContent = user.nickname || user.name || user.email || "User";
}

// ========== 退出登录 ==========
function logout() {
  localStorage.removeItem("login_user");
  localStorage.removeItem("auth_token");
  window.location.href = "../login.html";
}

// ========== 初始化：两页通用 ==========
applySystemSettings();
loadUserInfo();
applyTeacherLang();
