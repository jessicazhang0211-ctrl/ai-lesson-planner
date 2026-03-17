const dict = {
  zh: {
    appName: "AI 辅助备课系统",
    title: "学生注册",
    subtitle: "学生自助注册已关闭",
    name: "姓名",
    email: "邮箱",
    password: "密码",
    confirm: "确认密码",
    submit: "已关闭",
    goLogin: "去登录",
    teacher: "教师端",
    classLabel: "班级",
    hint: "学生账号由教师导入分配，请联系教师获取学号和初始密码",
    errors: {
      disabled: "学生不允许自助注册，请联系教师导入账号"
    }
  },
  en: {
    appName: "AI Lesson Planner",
    title: "Student Sign Up",
    subtitle: "Student self-signup is disabled",
    name: "Name",
    email: "Email",
    password: "Password",
    confirm: "Confirm password",
    submit: "Disabled",
    goLogin: "Go to sign in",
    teacher: "Teacher Portal",
    classLabel: "Class",
    hint: "Student accounts are assigned by teachers. Please ask your teacher for student ID and initial password",
    errors: {
      disabled: "Student self-signup is disabled. Please contact your teacher"
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

  $("nameLabel").childNodes[0].textContent = t.name + "\n            ";
  $("emailLabel").childNodes[0].textContent = t.email + "\n            ";
  $("passwordLabel").childNodes[0].textContent = t.password + "\n            ";
  $("confirmLabel").childNodes[0].textContent = t.confirm + "\n            ";
  $("classLabel").childNodes[0].textContent = t.classLabel + "\n            ";

  $("submitBtn").textContent = t.submit;
  $("goLoginLink").textContent = t.goLogin;
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

async function onSubmit(e) {
  e.preventDefault();
  setError(dict[lang].errors.disabled);
}

function bindEvents() {
  $("langToggle").addEventListener("click", (e) => {
    e.preventDefault();
    toggleLang();
  });

  $("registerForm").addEventListener("submit", onSubmit);
}

applyLang();
bindEvents();
setError(dict[lang].errors.disabled);
