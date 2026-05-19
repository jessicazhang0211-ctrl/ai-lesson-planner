import { apiRequest } from "./client.js";

export function loginTeacher({ email, password }) {
  return apiRequest("/api/auth/login", {
    method: "POST",
    auth: false,
    body: { email, password }
  });
}

export function loginStudent({ stuId, password }) {
  return apiRequest("/api/auth/login", {
    method: "POST",
    auth: false,
    body: { stu_id: stuId, password }
  });
}

export function registerTeacher({ name, email, password }) {
  return apiRequest("/api/auth/register", {
    method: "POST",
    auth: false,
    body: { name, email, password, role: "teacher" }
  });
}
