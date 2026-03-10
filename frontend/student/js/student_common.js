function getLocale() {
  return localStorage.getItem("locale") || "zh";
}

function applySystemSettings() {
  const fontSize = localStorage.getItem("font_size") || "medium";
  document.documentElement.setAttribute("data-font", fontSize);
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

async function apiGet(path) {
  const token = getToken();
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Authorization": `Bearer ${token}` }
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.code !== 0) throw new Error(data.message || "api error");
  return data.data;
}
