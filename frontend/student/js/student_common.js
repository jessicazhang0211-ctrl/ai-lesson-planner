const studentShellDict = {
  zh: {
    appName: "AI 辅助备课系统",
    menuSettings: "设置",
    menuLogout: "退出登录",
    navOverview: "学习概览",
    navPractice: "练习",
    navReview: "复习",
    navLessons: "教案资源",
    navScores: "成绩与学情",
    navSettings: "设置"
  },
  en: {
    appName: "AI Lesson Planner",
    menuSettings: "Settings",
    menuLogout: "Log out",
    navOverview: "Overview",
    navPractice: "Practice",
    navReview: "Review",
    navLessons: "Lessons",
    navScores: "Scores & Insights",
    navSettings: "Settings"
  }
};

const commonI18n = window.I18N || null;
if (commonI18n) commonI18n.registerDict("studentShell", studentShellDict);

function getLocale() {
  if (commonI18n) return commonI18n.getLocale();
  return (localStorage.getItem("locale") || "zh").toLowerCase().startsWith("en") ? "en" : "zh";
}

function applyStudentShellI18n(root) {
  const locale = getLocale();
  document.documentElement.lang = locale === "en" ? "en" : "zh-CN";
  if (commonI18n) {
    commonI18n.applyDataI18n("studentShell", root || document);
  }
}

if (commonI18n) {
  commonI18n.onLocaleChange(() => {
    applyStudentShellI18n(document);
  });
}

function applySystemSettings() {
  const fontSize = localStorage.getItem("font_size") || "medium";
  document.documentElement.setAttribute("data-font", fontSize);
  applyStudentShellI18n(document);
}

function toggleSidebar() {
  const sidebar = document.getElementById("sidebar");
  if (sidebar) sidebar.classList.toggle("collapsed");
}

function toggleUserMenu() {
  const menu = document.getElementById("userMenu");
  if (!menu) return;
  menu.style.display = menu.style.display === "block" ? "none" : "block";
}

document.addEventListener("click", (e) => {
  const menu = document.getElementById("userMenu");
  const topbar = document.querySelector(".topbar-right");
  if (!menu || !topbar) return;
  if (!topbar.contains(e.target)) menu.style.display = "none";
});

function goHome() {
  window.location.href = "./index.html";
}

function goSettings() {
  window.location.href = "./settings.html";
}

function logout() {
  localStorage.removeItem("login_user");
  localStorage.removeItem("auth_token");
  localStorage.removeItem("login_role");
  window.location.href = "../login.html";
}

function loadStudentProfile() {
  const raw = localStorage.getItem("login_user");
  if (!raw) return;
  const user = JSON.parse(raw);
  const name = user.nickname || user.name || user.email || "Student";
  const nameEl = document.getElementById("studentName");
  if (nameEl) nameEl.textContent = name;

  const avatar = localStorage.getItem("student_avatar");
  const avatarEl = document.getElementById("studentAvatar");
  if (avatar && avatarEl) avatarEl.src = avatar;
}

function requireLogin() {
  const token = localStorage.getItem("auth_token");
  const userRaw = localStorage.getItem("login_user") || "";
  let role = "";
  try {
    const user = JSON.parse(userRaw);
    role = user.role || "";
  } catch {
    role = "";
  }

  if (!token || role !== "student") {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("login_user");
    localStorage.removeItem("login_role");
    window.location.href = "./login.html";
  }
}

const API_BASE = "http://127.0.0.1:5000";

function getToken() {
  return localStorage.getItem("auth_token") || "";
}

function redirectToLoginOnAuthError(message) {
  const msg = String(message || "").toLowerCase();
  const hit = msg.includes("401") || msg.includes("invalid") || msg.includes("expired") || msg.includes("missing user") || msg.includes("token");
  if (!hit) return false;

  localStorage.removeItem("auth_token");
  localStorage.removeItem("login_user");
  localStorage.removeItem("login_role");

  const locale = getLocale();
  const notice = locale === "en" ? "Session expired. Please sign in again." : "登录已失效，请重新登录。";
  if (!window.location.pathname.toLowerCase().endsWith("/login.html")) {
    alert(notice);
    window.location.href = "./login.html";
  }
  return true;
}

async function apiGet(path) {
  const token = getToken();
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Authorization": `Bearer ${token}` }
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.code !== 0) {
    const mustChangePassword = !!(data && data.data && data.data.must_change_password);
    const msg = String(data.message || "api error");

    if (res.status === 401 || redirectToLoginOnAuthError(msg)) {
      throw new Error(msg || "401 unauthorized");
    }

    if (mustChangePassword || msg.includes("password reset required")) {
      localStorage.setItem("must_change_password", "1");
      const locale = getLocale();
      const notice = locale === "en"
        ? "Please change your initial password in Settings before accessing assignments."
        : "请先在设置中修改初始密码后再使用作业功能。";
      const inSettings = window.location.pathname.toLowerCase().endsWith("/settings.html");
      if (!inSettings) {
        alert(notice);
        window.location.href = "./settings.html";
      }
    }
    throw new Error(msg);
  }
  return data.data;
}

function normalizeAssignments(payload) {
  if (Array.isArray(payload)) return payload;
  if (!payload || typeof payload !== "object") return [];

  if (Array.isArray(payload.assignments)) return payload.assignments;
  if (Array.isArray(payload.items)) return payload.items;
  if (Array.isArray(payload.list)) return payload.list;
  if (Array.isArray(payload.rows)) return payload.rows;

  return [];
}
