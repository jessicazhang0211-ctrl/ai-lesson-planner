const dict = {
  zh: {
    appName: "AI 辅助备课系统",
    title: "学生登录",
    subtitle: "欢迎回来，请登录继续",
    email: "邮箱",
    password: "密码",
    remember: "记住我",
    forgot: "忘记密码？",
    submit: "登录",
    register: "注册",
    teacher: "教师端",
    hint: "使用测试账号：test@example.com / 123456",
    errors: {
      required: "请填写完整信息",
      invalidEmail: "请输入有效邮箱",
      loginFailed: "登录失败，请检查账号或密码"
    },
    alerts: {
      forgot: "忘记密码流程（待做）"
    }
  },
  en: {
    appName: "AI Lesson Planner",
    title: "Student sign in",
    subtitle: "Welcome back. Please sign in to continue.",
    email: "Email",
    password: "Password",
    remember: "Remember me",
    forgot: "Forgot password?",
    submit: "Sign in",
    register: "Sign up",
    teacher: "Teacher Portal",
    hint: "Test account: test@example.com / 123456",
    errors: {
      required: "Please complete all fields",
      invalidEmail: "Please enter a valid email",
      loginFailed: "Login failed. Please check your credentials."
    },
    alerts: {
      forgot: "Forgot password flow (TODO)"
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

  $("emailLabel").childNodes[0].textContent = t.email + "\n            ";
  $("passwordLabel").childNodes[0].textContent = t.password + "\n            ";

  $("rememberText").textContent = t.remember;
  $("forgotLink").textContent = t.forgot;
  $("submitBtn").textContent = t.submit;

  $("registerLink").textContent = t.register;
  $("teacherLink").textContent = t.teacher;

  $("hintText").textContent = t.hint;

  $("langToggle").textContent = lang === "zh" ? "EN" : "中文";
}

function toggleLang() {
  lang = lang === "zh" ? "en" : "zh";
  localStorage.setItem("locale", lang);
  applyLang();
}

async function loginSubmit(e) {
  e.preventDefault();
  setError("");

  const email = $("email").value.trim();
  const password = $("password").value.trim();

  if (!email || !password) {
    setError(dict[lang].errors.required);
    return;
  }
  if (!isValidEmail(email)) {
    setError(dict[lang].errors.invalidEmail);
    return;
  }

  try {
    const res = await fetch("http://127.0.0.1:5000/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });

    const data = await res.json();

    if (data.code === 0) {
      const user = data.data && data.data.user ? data.data.user : { email };

      localStorage.setItem("login_user", JSON.stringify(user));
      localStorage.setItem("login_role", "student");
      if (data.data && data.data.token) {
        localStorage.setItem("auth_token", data.data.token);
      }

      localStorage.setItem("prefill_email", user.email || email);

      window.location.href = "./index.html";
      return;
    }

    setError(dict[lang].errors.loginFailed);
  } catch {
    setError(lang === "zh" ? "网络错误：无法连接后端" : "Network error: backend not reachable");
  }
}

function bindEvents() {
  $("langToggle").addEventListener("click", (e) => {
    e.preventDefault();
    toggleLang();
  });

  $("forgotLink").addEventListener("click", (e) => {
    e.preventDefault();
    alert(dict[lang].alerts.forgot);
  });

  $("loginForm").addEventListener("submit", loginSubmit);
}

function prefillFromRegister() {
  const email = localStorage.getItem("prefill_email");
  if (email && $("email")) {
    $("email").value = email;
    if ($("password")) $("password").focus();
    localStorage.removeItem("prefill_email");
  }
}

applyLang();
bindEvents();
prefillFromRegister();
