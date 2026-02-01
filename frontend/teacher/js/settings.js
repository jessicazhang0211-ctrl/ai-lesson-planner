const settingsDict = {
  zh: {
    pageTitle: "设置",

    sectionPersonal: "个人信息",
    itemProfile: "个人资料",
    itemAccount: "账号设置",

    sectionGeneral: "通用",
    itemLanguage: "语言设置",
    itemFont: "字体设置",

    // Panels
    panelProfileTitle: "个人资料",
    panelProfileDesc: "查看你的基本信息（后续可扩展头像/昵称修改）。",
    name: "姓名",
    email: "邮箱",
    phone: "手机号",
    role: "角色",

    panelAccountTitle: "账号设置",
    panelAccountDesc: "可修改密码、手机号、邮箱（后续接后端接口）。",
    currentPassword: "当前密码",
    newPassword: "新密码",
    confirmPassword: "确认新密码",
    newEmail: "新邮箱",
    newPhone: "新手机号",

    panelLanguageTitle: "语言设置",
    panelLanguageDesc: "修改后将同步整个系统界面语言。",
    language: "语言",
    chinese: "中文",
    english: "English",

    panelFontTitle: "字体设置",
    panelFontDesc: "修改后将同步整个系统字体大小。",
    font: "字体大小",
    small: "小",
    medium: "中",
    large: "大",

    save: "保存",
    saved: "已保存",
    pwdMismatch: "两次输入的新密码不一致",
  },

  en: {
    pageTitle: "Settings",

    sectionPersonal: "Personal",
    itemProfile: "Profile",
    itemAccount: "Account",

    sectionGeneral: "General",
    itemLanguage: "Language",
    itemFont: "Font Size",

    panelProfileTitle: "Profile",
    panelProfileDesc: "View your basic info (you can extend this to edit avatar/name later).",
    name: "Name",
    email: "Email",
    phone: "Phone",
    role: "Role",

    panelAccountTitle: "Account",
    panelAccountDesc: "Update password, phone, and email (connect backend later).",
    currentPassword: "Current password",
    newPassword: "New password",
    confirmPassword: "Confirm new password",
    newEmail: "New email",
    newPhone: "New phone",

    panelLanguageTitle: "Language",
    panelLanguageDesc: "Changes will apply to the whole system UI.",
    language: "Language",
    chinese: "Chinese",
    english: "English",

    panelFontTitle: "Font Size",
    panelFontDesc: "Changes will apply to the whole system UI.",
    font: "Font size",
    small: "Small",
    medium: "Medium",
    large: "Large",

    save: "Save",
    saved: "Saved",
    pwdMismatch: "New passwords do not match",
  }
};

function getLocale() {
  return localStorage.getItem("locale") || "zh";
}

function t(key) {
  return settingsDict[getLocale()][key] || key;
}

function setTexts() {
  // 页面标题
  const title = document.getElementById("pageTitle");
  if (title) title.textContent = t("pageTitle");

  // 左侧分组/菜单
  document.querySelectorAll("[data-s-i18n]").forEach(el => {
    const k = el.getAttribute("data-s-i18n");
    el.textContent = t(k);
  });

  // 顶栏系统名（可选）
  const appName = document.getElementById("appName");
  if (appName) appName.textContent = getLocale() === "zh" ? "AI 辅助备课系统" : "AI Lesson Planner";
}

function getUser() {
  try {
    return JSON.parse(localStorage.getItem("login_user") || "{}");
  } catch {
    return {};
  }
}

let currentView = "profile";

function renderPanel(view) {
  const panel = document.getElementById("settingsPanel");
  if (!panel) return;

  currentView = view;

  if (view === "profile") {
    const user = getUser();
    panel.innerHTML = `
      <div class="panel-title">${t("panelProfileTitle")}</div>
      <div class="panel-desc">${t("panelProfileDesc")}</div>

      <div class="field">
        <label>${t("name")}</label>
        <input value="${(user.name || "—")}" disabled />
      </div>
      <div class="field">
        <label>${t("email")}</label>
        <input value="${(user.email || "—")}" disabled />
      </div>
      <div class="field">
        <label>${t("phone")}</label>
        <input value="${(user.phone || "—")}" disabled />
      </div>
      <div class="field">
        <label>${t("role")}</label>
        <input value="${(user.role || "teacher")}" disabled />
      </div>
    `;
    return;
  }

  if (view === "account") {
    panel.innerHTML = `
      <div class="panel-title">${t("panelAccountTitle")}</div>
      <div class="panel-desc">${t("panelAccountDesc")}</div>

      <div class="field">
        <label>${t("currentPassword")}</label>
        <input id="curPwd" type="password" placeholder="••••••••" />
      </div>
      <div class="field">
        <label>${t("newPassword")}</label>
        <input id="newPwd" type="password" placeholder="••••••••" />
      </div>
      <div class="field">
        <label>${t("confirmPassword")}</label>
        <input id="confirmPwd" type="password" placeholder="••••••••" />
      </div>

      <div class="field">
        <label>${t("newEmail")}</label>
        <input id="newEmail" type="email" placeholder="name@example.com" />
      </div>
      <div class="field">
        <label>${t("newPhone")}</label>
        <input id="newPhone" type="text" placeholder="+44..." />
      </div>

      <div class="panel-actions">
        <a href="#" id="saveAccount" class="primary-link">${t("save")}</a>
      </div>
    `;

    document.getElementById("saveAccount").addEventListener("click", (e) => {
      e.preventDefault();

      const np = document.getElementById("newPwd").value.trim();
      const cp = document.getElementById("confirmPwd").value.trim();
      if (np || cp) {
        if (np !== cp) {
          alert(t("pwdMismatch"));
          return;
        }
      }

      // TODO: 这里未来接后端接口（PUT /api/user/account）
      // 现在先本地演示：把邮箱/电话写到 login_user 里
      const user = getUser();
      const newEmail = document.getElementById("newEmail").value.trim();
      const newPhone = document.getElementById("newPhone").value.trim();

      if (newEmail) user.email = newEmail;
      if (newPhone) user.phone = newPhone;

      localStorage.setItem("login_user", JSON.stringify(user));
      alert(t("saved"));
    });

    return;
  }

  if (view === "language") {
    const lang = getLocale();
    panel.innerHTML = `
      <div class="panel-title">${t("panelLanguageTitle")}</div>
      <div class="panel-desc">${t("panelLanguageDesc")}</div>

      <div class="field">
        <label>${t("language")}</label>
        <select id="langSelect" style="height:38px;border:1px solid #e5e6eb;border-radius:8px;padding:0 10px;">
          <option value="zh">${t("chinese")}</option>
          <option value="en">${t("english")}</option>
        </select>
      </div>

      <div class="panel-actions">
        <a href="#" id="savePrefs" class="primary-link">${t("save")}</a>
      </div>
    `;

    document.getElementById("langSelect").value = lang;

    document.getElementById("savePrefs").addEventListener("click", (e) => {
      e.preventDefault();
      localStorage.setItem("locale", document.getElementById("langSelect").value);

      // 立即应用到全系统（teacher.js 提供）
      if (typeof applySystemSettings === "function") applySystemSettings();
      if (typeof applyTeacherLang === "function") applyTeacherLang();

      // 刷新本页文本 & 重新渲染当前 panel
      setTexts();
      renderPanel("language");
      alert(t("saved"));
    });

    return;
  }

  if (view === "font") {
    const font = localStorage.getItem("font_size") || "medium";
    panel.innerHTML = `
      <div class="panel-title">${t("panelFontTitle")}</div>
      <div class="panel-desc">${t("panelFontDesc")}</div>

      <div class="field">
        <label>${t("font")}</label>
        <select id="fontSelect" style="height:38px;border:1px solid #e5e6eb;border-radius:8px;padding:0 10px;">
          <option value="small">${t("small")}</option>
          <option value="medium">${t("medium")}</option>
          <option value="large">${t("large")}</option>
        </select>
      </div>

      <div class="panel-actions">
        <a href="#" id="savePrefs" class="primary-link">${t("save")}</a>
      </div>
    `;

    document.getElementById("fontSelect").value = font;

    document.getElementById("savePrefs").addEventListener("click", (e) => {
      e.preventDefault();
      localStorage.setItem("font_size", document.getElementById("fontSelect").value);

      if (typeof applySystemSettings === "function") applySystemSettings();

      // 本页文本不需要重渲染，但为了统一体验也可以保持
      setTexts();
      renderPanel("font");
      alert(t("saved"));
    });

    return;
  }
}

function bindLeftNav() {
  document.querySelectorAll(".settings-item").forEach(item => {
    item.addEventListener("click", (e) => {
      e.preventDefault();

      document.querySelectorAll(".settings-item").forEach(i => i.classList.remove("active"));
      item.classList.add("active");

      const view = item.getAttribute("data-view");
      renderPanel(view);
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  setTexts();
  bindLeftNav();
  renderPanel("profile");
});
