const dict = {
  zh: {
    appName: "AI 辅助备课系统",
    title: "学生注册",
    subtitle: "创建学生账号后开始学习",
    name: "姓名",
    email: "邮箱",
    password: "密码",
    confirm: "确认密码",
    submit: "注册",
    goLogin: "去登录",
    teacher: "教师端",
    classLabel: "班级",
    hint: "注册后将跳转到登录页",
    errors: {
      required: "请填写完整信息",
      invalidEmail: "请输入有效邮箱",
      pwdTooShort: "密码至少 6 位",
      pwdMismatch: "两次密码不一致",
      failed: "注册失败，请稍后重试"
    },
    alerts: {
      success: "注册成功！即将跳转到登录页"
    }
  },
  en: {
    appName: "AI Lesson Planner",
    title: "Student sign up",
    subtitle: "Create a student account to start learning",
    name: "Name",
    email: "Email",
    password: "Password",
    confirm: "Confirm password",
    submit: "Sign up",
    goLogin: "Go to sign in",
    teacher: "Teacher Portal",
    classLabel: "Class",
    hint: "You will be redirected to the login page after signing up",
    errors: {
      required: "Please complete all fields",
      invalidEmail: "Please enter a valid email",
      pwdTooShort: "Password must be at least 6 characters",
      pwdMismatch: "Passwords do not match",
      failed: "Sign up failed. Please try again."
    },
    alerts: {
      success: "Sign up successful! Redirecting to login..."
    }
  }
};

function $(id) { return document.getElementById(id); }

let lang = localStorage.getItem("locale") || "zh";

function setError(msg) {
  const el = $("error");
  if (!msg) {
    el.style.display = "none";
    el.textContent = "";
    return;
  }
  el.style.display = "block";
  el.textContent = msg;
}

function isValidEmail(v) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v);
}

function applyLang() {
  const t = dict[lang];
  document.documentElement.lang = lang === "zh" ? "zh" : "en";

  $("appName").textContent = t.appName;
  $("title").textContent = t.title;
  $("subtitle").textContent = t.subtitle;

  $("nameLabel").childNodes[0].textContent = t.name + "\n            ";
  $("emailLabel").childNodes[0].textContent = t.email + "\n            ";
  $("passwordLabel").childNodes[0].textContent = t.password + "\n            ";
  $("confirmLabel").childNodes[0].textContent = t.confirm + "\n            ";
  $("classLabel").childNodes[0].textContent = t.classLabel + "\n            ";

  $("submitBtn").textContent = t.submit;
  $("goLoginLink").textContent = t.goLogin;
  $("teacherLink").textContent = t.teacher;
  $("hintText").textContent = t.hint;

  $("langToggle").textContent = lang === "zh" ? "EN" : "中文";
}

function toggleLang() {
  lang = lang === "zh" ? "en" : "zh";
  localStorage.setItem("locale", lang);
  applyLang();
}

async function onSubmit(e) {
  e.preventDefault();
  setError("");

  const name = $("name").value.trim();
  const email = $("email").value.trim();
  const password = $("password").value.trim();
  const confirm = $("confirm").value.trim();
  const classId = $("classId").value;

  const t = dict[lang];

  if (!name || !email || !password || !confirm || !classId) {
    setError(t.errors.required);
    return;
  }
  if (!isValidEmail(email)) {
    setError(t.errors.invalidEmail);
    return;
  }
  if (password.length < 6) {
    setError(t.errors.pwdTooShort);
    return;
  }
  if (password !== confirm) {
    setError(t.errors.pwdMismatch);
    return;
  }

  try {
    const res = await fetch("http://127.0.0.1:5000/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email, password, role: "student", class_id: Number(classId) })
    });

    const data = await res.json();

    if (data.code === 0) {
      localStorage.setItem("prefill_email", email);
      localStorage.setItem("prefill_name", name);

      alert(t.alerts.success);
      window.location.href = "./login.html";
      return;
    }

    setError(data.message || t.errors.failed);
  } catch {
    setError(lang === "zh" ? "网络错误：无法连接后端" : "Network error: backend not reachable");
  }
}

function bindEvents() {
  $("langToggle").addEventListener("click", (e) => {
    e.preventDefault();
    toggleLang();
  });

  $("registerForm").addEventListener("submit", onSubmit);
}

async function loadClasses() {
  const select = $("classId");
  if (!select) return;
  try {
    const res = await fetch("http://127.0.0.1:5000/api/class/public");
    const data = await res.json();
    const list = (data && data.code === 0) ? (data.data || []) : [];
    if (!list.length) {
      select.innerHTML = "";
      return;
    }
    select.innerHTML = list.map(c => `<option value="${c.id}">${c.name}</option>`).join("");
  } catch {
    select.innerHTML = "";
  }
}

applyLang();
bindEvents();
loadClasses();
