export function readJson(key, fallback = null) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

export function writeJson(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

export function clearAuthStorage() {
  localStorage.removeItem("auth_token");
  localStorage.removeItem("login_user");
  localStorage.removeItem("login_role");
}
