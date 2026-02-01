const dict = {
  zh: {
    appName: "AI 辅助备课系统",
    title: "登录界面",
    subtitle: "欢迎回来，请登录继续",
    email: "邮箱",
    password: "密码",
    remember: "记住我",
    forgot: "忘记密码？",
    submit: "登录",
    register: "注册",
    student: "学生端",
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
    title: "Sign in",
    subtitle: "Welcome back. Please sign in to continue.",
    email: "Email",
    password: "Password",
    remember: "Remember me",
    forgot: "Forgot password?",
    submit: "Sign in",
    register: "Sign up",
    student: "Student Portal",
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

  // label 文本（保持 input 不变）
  $("emailLabel").childNodes[0].textContent = t.email + "\n            ";
  $("passwordLabel").childNodes[0].textContent = t.password + "\n            ";

  $("rememberText").textContent = t.remember;
  $("forgotLink").textContent = t.forgot;
  $("submitBtn").textContent = t.submit;

  $("registerLink").textContent = t.register;
  $("studentLink").textContent = t.student;

  $("hintText").textContent = t.hint;

  // 右上角切换显示
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

  // 调 Flask 后端（你现在用的假登录）
  try {
    const res = await fetch("http://127.0.0.1:5000/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });

    const data = await res.json();

    if (data.code === 0) {
      // ✅ 1) 保存登录用户信息（供教师端校验/显示）
      // 后端返回格式：data.data.user
      const user = data.data && data.data.user ? data.data.user : { email };

      localStorage.setItem("login_user", JSON.stringify(user));

      // （可选）记住邮箱：下次打开登录页自动填
      localStorage.setItem("prefill_email", user.email || email);

      // ✅ 2) 跳转到教师端主界面
      // 注意路径：如果 login.html 在 frontend 根目录，而教师端在 frontend/teacher/
      window.location.href = "./teacher/index.html";

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

    // ✅ 自动聚焦到密码框（更像真实产品）
    if ($("password")) $("password").focus();

    // ✅ 用完就删，避免下次还一直填
    localStorage.removeItem("prefill_email");
  }
}


applyLang();
bindEvents();
prefillFromRegister();
