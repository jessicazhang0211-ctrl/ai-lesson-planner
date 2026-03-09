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
  if (!token) {
    window.location.href = "./login.html";
  }
}
