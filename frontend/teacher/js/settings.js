// ========== i18n ==========
const settingsDict = {
  zh: {
    pageTitle: "设置",

    sectionPersonal: "个人信息",
    itemProfile: "个人资料",
    itemWork: "工作信息",
    itemAccount: "账号设置",

    sectionGeneral: "通用",
    itemLanguage: "语言设置",
    itemFont: "字体设置",

    // profile/work labels
    nickname: "用户昵称",
    userId: "用户ID",
    gender: "性别",
    bio: "个人简介",
    male: "男",
    female: "女",
    unset: "未选择",
    phone: "手机号",

    school: "学校名称",
    major: "专业",
    jobTitle: "职位名称",

    // panels titles
    panelProfileTitle: "个人资料",
    panelProfileDesc: "头像 + 手机号遮罩 + 昵称（悬停可编辑）。",
    panelWorkTitle: "工作信息",
    panelWorkDesc: "学校与岗位信息（悬停可编辑）。",

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

    edit: "编辑",
    save: "保存",
    cancel: "取消",
    saved: "已保存",
    saving: "保存中...",
    saveOk: "保存成功",
    saveFail: "保存失败，请重试",
    pwdMismatch: "两次输入的新密码不一致",
  },

  en: {
    pageTitle: "Settings",

    sectionPersonal: "Personal",
    itemProfile: "Profile",
    itemWork: "Work Info",
    itemAccount: "Account",

    sectionGeneral: "General",
    itemLanguage: "Language",
    itemFont: "Font Size",

    nickname: "Nickname",
    userId: "User ID",
    gender: "Gender",
    bio: "Bio",
    male: "Male",
    female: "Female",
    unset: "Not set",
    phone: "Phone",

    school: "School",
    major: "Major",
    jobTitle: "Job Title",

    panelProfileTitle: "Profile",
    panelProfileDesc: "Avatar + masked phone + nickname (hover to edit).",
    panelWorkTitle: "Work Info",
    panelWorkDesc: "School & job info (hover to edit).",

    panelAccountTitle: "Account",
    panelAccountDesc: "Update password / phone / email (connect backend later).",
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
    panelFontDesc: "Changes will apply to the whole system font size.",
    font: "Font size",
    small: "Small",
    medium: "Medium",
    large: "Large",

    edit: "Edit",
    save: "Save",
    cancel: "Cancel",
    saved: "Saved",
    saving: "Saving...",
    saveOk: "Saved",
    saveFail: "Save failed. Please try again.",
    pwdMismatch: "New passwords do not match",
  }
};

function getLocale() {
  return localStorage.getItem("locale") || "zh";
}
function t(key) {
  const lang = getLocale();
  return (settingsDict[lang] && settingsDict[lang][key]) ? settingsDict[lang][key] : key;
}

// ========== API / user cache ==========
let me = null;
let currentView = "profile";
const API_BASE = "http://127.0.0.1:5000";

function authHeaders() {
  const u = JSON.parse(localStorage.getItem("login_user") || "{}");
  return { "Content-Type": "application/json", "X-User-Id": u.id || u.user_id || "" };
}

async function apiGetMe() {
  const res = await fetch(`${API_BASE}/api/user/me`, { headers: authHeaders() });
  if (!res.ok) throw new Error("GET /api/user/me failed");
  return res.json();
}

async function apiPatchMe(patch) {
  const res = await fetch(`${API_BASE}/api/user/me`, {
    method: "PATCH",
    headers: authHeaders(),
    body: JSON.stringify(patch)
  });
  const data = await res.json();
  if (!res.ok || data.code !== 0) throw new Error(data.message || "PATCH /api/user/me failed");
  return data;
}

async function loadMe() {
  const r = await apiGetMe();
  me = r.data;
}

function maskPhone(phone) {
  if (!phone) return "—";
  const s = String(phone);
  if (s.length < 7) return "****";
  return s.slice(0, 3) + "****" + s.slice(-4);
}

// ========== UI text ==========
function setTexts() {
  const title = document.getElementById("pageTitle");
  if (title) title.textContent = t("pageTitle");

  document.querySelectorAll("[data-s-i18n]").forEach(el => {
    const k = el.getAttribute("data-s-i18n");
    el.textContent = t(k);
  });

  const appName = document.getElementById("appName");
  if (appName) appName.textContent = getLocale() === "zh" ? "AI 辅助备课系统" : "AI Lesson Planner";
}

// ========== helpers for editable rows ==========
function escapeHtml(s) {
  return String(s ?? "")
    .replaceAll("&","&amp;")
    .replaceAll("<","&lt;")
    .replaceAll(">","&gt;")
    .replaceAll('"',"&quot;")
    .replaceAll("'","&#39;");
}

function rowBase(key, label, valueHtml, editable = true) {
  return `
    <div class="row-item" data-row="${key}">
      <div class="row-left">
        <div class="row-label">${label}</div>
        <div class="row-value" data-value>${valueHtml}</div>
      </div>
      <div class="row-actions">
        ${
          editable
            ? `<a href="#" class="edit-link" data-action="edit">${t("edit")}</a>`
            : `<span class="muted">—</span>`
        }
      </div>
    </div>
  `;
}

// ========== panels ==========
function renderProfilePanel(panel) {
  const nickname = me?.nickname || me?.name || "—";
  panel.innerHTML = `
    <div class="panel-title">${t("panelProfileTitle")}</div>
    <div class="panel-desc">${t("panelProfileDesc")}</div>

    <div class="profile-head">
      <div class="profile-meta">
        <img class="profile-avatar" src="${me?.avatar_url || "../assets/avatar.png"}" alt="avatar">
        <div>
          <div class="profile-name">${escapeHtml(nickname)}</div>
          <div class="profile-sub">${t("phone")}：${maskPhone(me?.phone)}</div>
        </div>
      </div>
    </div>

    ${rowBase("nickname", t("nickname"), escapeHtml(me?.nickname || "—"))}
    ${rowBase("id", t("userId"), escapeHtml(me?.id || "—"), false)}
    ${rowBase("gender", t("gender"), escapeHtml(me?.gender || t("unset")))}
    ${rowBase("phone", t("phone"), escapeHtml(me?.phone || "—"))}
    ${rowBase("email", t("email"), escapeHtml(me?.email || "—"))}
    ${rowBase("bio", t("bio"), escapeHtml(me?.bio || "—"))}
  `;
  bindRowEditors(panel);
}

function renderWorkPanel(panel) {
  panel.innerHTML = `
    <div class="panel-title">${t("panelWorkTitle")}</div>
    <div class="panel-desc">${t("panelWorkDesc")}</div>

    ${rowBase("school", t("school"), escapeHtml(me?.school || "—"))}
    ${rowBase("major", t("major"), escapeHtml(me?.major || "—"))}
    ${rowBase("job_title", t("jobTitle"), escapeHtml(me?.job_title || "—"))}
  `;
  bindRowEditors(panel);
}

function renderAccountPanel(panel) {
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
    if ((np || cp) && np !== cp) return alert(t("pwdMismatch"));

    // 这里你后续接真正后端接口
    alert(t("saved"));
  });
}

function renderLanguagePanel(panel) {
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

    if (typeof applySystemSettings === "function") applySystemSettings();
    if (typeof applyTeacherLang === "function") applyTeacherLang();

    setTexts();
    rerenderCurrent();
    alert(t("saved"));
  });
}

function renderFontPanel(panel) {
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
      <a href="#" id="saveFont" class="primary-link">${t("save")}</a>
    </div>
  `;
  document.getElementById("fontSelect").value = font;

  document.getElementById("saveFont").addEventListener("click", (e) => {
    e.preventDefault();
    localStorage.setItem("font_size", document.getElementById("fontSelect").value);

    if (typeof applySystemSettings === "function") applySystemSettings();

    setTexts();
    rerenderCurrent();
    alert(t("saved"));
  });
}

// ========== editable rows ==========
function bindRowEditors(panel) {
  panel.querySelectorAll("[data-row]").forEach(row => {
    const btn = row.querySelector("[data-action='edit']");
    if (!btn) return;
    btn.addEventListener("click", e => {
      e.preventDefault();
      enterEditMode(row);
    });
  });
}

function enterEditMode(row) {
  const key = row.dataset.row;
  const valueEl = row.querySelector("[data-value]");
  const actions = row.querySelector(".row-actions");

  const oldDisplay = valueEl.innerHTML;
  const oldValue = (me && me[key]) ? me[key] : "";

  let editorHtml = "";
  if (key === "gender") {
    editorHtml = `
      <select class="inline-select" data-editor>
        <option value="">${t("unset")}</option>
        <option value="${t("male")}">${t("male")}</option>
        <option value="${t("female")}">${t("female")}</option>
      </select>
    `;
  } else if (key === "bio") {
    editorHtml = `<textarea class="inline-textarea" data-editor></textarea>`;
  } else {
    editorHtml = `<input class="inline-input" data-editor />`;
  }

  valueEl.innerHTML = editorHtml;
  const editor = row.querySelector("[data-editor]");
  editor.value = oldValue;

  actions.innerHTML = `
    <a href="#" class="edit-link" data-action="save">${t("save")}</a>
    <a href="#" class="edit-link" data-action="cancel">${t("cancel")}</a>
    <span class="muted" style="display:none" data-saving>${t("saving")}</span>
  `;

  actions.querySelector("[data-action='cancel']").onclick = (e) => {
    e.preventDefault();
    valueEl.innerHTML = oldDisplay;
    actions.innerHTML = `<a href="#" class="edit-link" data-action="edit">${t("edit")}</a>`;
    actions.querySelector("[data-action='edit']").onclick = (ev) => {
      ev.preventDefault();
      enterEditMode(row);
    };
  };

  actions.querySelector("[data-action='save']").onclick = async (e) => {
    e.preventDefault();
    const saving = actions.querySelector("[data-saving]");
    saving.style.display = "inline";

    const newVal = editor.value.trim();

    try {
      const r = await apiPatchMe({ [key]: newVal });
      me = r.data.user;
      rerenderCurrent();
      alert(t("saveOk"));
    } catch (err) {
      console.error(err);
      saving.style.display = "none";
      alert(t("saveFail"));
    }
  };
}

// ========== router ==========
function renderCurrent(panel) {
  if (currentView === "profile") return renderProfilePanel(panel);
  if (currentView === "work") return renderWorkPanel(panel);
  if (currentView === "account") return renderAccountPanel(panel);
  if (currentView === "language") return renderLanguagePanel(panel);
  if (currentView === "font") return renderFontPanel(panel);
}

function rerenderCurrent() {
  const panel = document.getElementById("settingsPanel");
  if (!panel) return;
  renderCurrent(panel);
}

function bindLeftNav() {
  document.querySelectorAll(".settings-item").forEach(item => {
    item.addEventListener("click", (e) => {
      e.preventDefault();
      document.querySelectorAll(".settings-item").forEach(i => i.classList.remove("active"));
      item.classList.add("active");

      currentView = item.getAttribute("data-view");
      rerenderCurrent();
    });
  });
}

// ========== init ==========
document.addEventListener("DOMContentLoaded", async () => {
  setTexts();
  bindLeftNav();

  try {
    await loadMe();
  } catch (e) {
    console.error("loadMe failed", e);
    alert("无法加载用户信息，请重新登录");
    return;
  }

  currentView = "profile";
  rerenderCurrent();
});
