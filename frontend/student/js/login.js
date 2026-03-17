const dict = {
  zh: {
    appName: "AI 辅助备课系统",
    title: "学生登录",
    subtitle: "欢迎回来，请登录继续",
    stuId: "学号",
    password: "密码",
    remember: "记住我",
    forgot: "忘记密码？",
    submit: "登录",
    teacher: "教师端",
    hint: "使用教师分配的学号和初始密码登录：123456",
    errors: {
      required: "请填写完整信息",
      loginFailed: "登录失败，请检查学号或密码",
      network: "网络错误：无法连接后端"
    },
    alerts: {
      forgot: "忘记密码流程（待做）"
    }
  },
  en: {
    appName: "AI Lesson Planner",
    title: "Student sign in",
    subtitle: "Welcome back. Please sign in to continue.",
    stuId: "Student ID",
    password: "Password",
    remember: "Remember me",
    forgot: "Forgot password?",
    submit: "Sign in",
    teacher: "Teacher Portal",
    hint: "Use your teacher-assigned student ID and initial password: 123456",
    errors: {
      required: "Please complete all fields",
      loginFailed: "Login failed. Please check your student ID or password.",
      network: "Network error: backend not reachable"
    },
    alerts: {
      forgot: "Forgot password flow (TODO)"
    }
  }
};

function $(id) { return document.getElementById(id); }

let lang = localStorage.getItem("locale") || "zh";
if (window.I18N) lang = window.I18N.getLocale();

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

function applyLang() {
  const t = dict[lang];

  document.documentElement.lang = lang === "zh" ? "zh" : "en";

  $("appName").textContent = t.appName;
  $("title").textContent = t.title;
  $("subtitle").textContent = t.subtitle;

  $("stuIdLabel").childNodes[0].textContent = t.stuId + "\n            ";
  $("passwordLabel").childNodes[0].textContent = t.password + "\n            ";

  $("rememberText").textContent = t.remember;
  $("forgotLink").textContent = t.forgot;
  $("submitBtn").textContent = t.submit;

  $("teacherLink").textContent = t.teacher;

  $("hintText").textContent = t.hint;

  $("langToggle").textContent = lang === "zh" ? "EN" : "ZH";
}

function toggleLang() {
  lang = lang === "zh" ? "en" : "zh";
  if (window.I18N) window.I18N.setLocale(lang);
  else localStorage.setItem("locale", lang);
  applyLang();
}

async function loginSubmit(e) {
  e.preventDefault();
  setError("");

  const stuId = $("stuId").value.trim();
  const password = $("password").value.trim();

  if (!stuId || !password) {
    setError(dict[lang].errors.required);
    return;
  }

  try {
    const res = await fetch("http://127.0.0.1:5000/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ stu_id: stuId, password })
    });

    const data = await res.json();

    if (data.code === 0) {
      const user = data.data && data.data.user ? data.data.user : { stu_id: stuId };

      localStorage.setItem("login_user", JSON.stringify(user));
      localStorage.setItem("login_role", "student");
      if (data.data && data.data.token) {
        localStorage.setItem("auth_token", data.data.token);
      }

      localStorage.setItem("prefill_stu_id", stuId);

      window.location.href = "./index.html";
      return;
    }

    setError(dict[lang].errors.loginFailed);
  } catch {
    setError(dict[lang].errors.network);
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
  const stuId = localStorage.getItem("prefill_stu_id");
  if (stuId && $("stuId")) {
    $("stuId").value = stuId;
    if ($("password")) $("password").focus();
    localStorage.removeItem("prefill_stu_id");
  }
}

applyLang();
bindEvents();
prefillFromRegister();
