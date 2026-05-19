import { clearAuthStorage, readJson } from "../utils/storage.js";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:5000";

export class ApiError extends Error {
  constructor(message, status, payload) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

export function getToken() {
  return localStorage.getItem("auth_token") || "";
}

export async function apiRequest(path, options = {}) {
  const {
    method = "GET",
    body,
    headers = {},
    auth = true,
    raw = false
  } = options;

  const requestHeaders = new Headers(headers);
  const hasBody = body !== undefined && body !== null;
  const isForm = typeof FormData !== "undefined" && body instanceof FormData;

  if (auth) {
    const token = getToken();
    if (token) requestHeaders.set("Authorization", `Bearer ${token}`);
    const user = readJson("login_user", {});
    const userId = user?.id || user?.user_id;
    if (userId) requestHeaders.set("X-User-Id", String(userId));
  }

  if (hasBody && !isForm && !requestHeaders.has("Content-Type")) {
    requestHeaders.set("Content-Type", "application/json");
  }

  const url = path.startsWith("http") ? path : `${API_BASE_URL}${path}`;
  const response = await fetch(url, {
    method,
    headers: requestHeaders,
    body: hasBody ? (isForm ? body : JSON.stringify(body)) : undefined
  });

  if (raw) return response;

  const payload = await response.json().catch(() => ({}));
  const ok = response.ok && (payload.code === undefined || payload.code === 0);

  if (!ok) {
    if (response.status === 401) clearAuthStorage();
    throw new ApiError(payload.message || response.statusText || "Request failed", response.status, payload);
  }

  return payload.data ?? payload;
}
