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

    school: "学校名称",
    major: "专业",
    jobTitle: "职位名称",

    // panels titles
    panelProfileTitle: "个人资料",
    panelProfileDesc: "头像 + 昵称（悬停可编辑）。",
    panelWorkTitle: "工作信息",
    panelWorkDesc: "学校与岗位信息（选择填写）。",

    panelAccountTitle: "账号设置",
    panelAccountDesc: "修改密码（需验证当前密码）。",
    currentPassword: "当前密码",
    newPassword: "新密码",
    confirmPassword: "确认新密码",

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
    pwdWrong: "当前密码错误",
    pwdFieldsRequired: "请填写所有密码字段",
    loadUserFail: "无法加载用户信息，请重新登录"
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

    school: "School",
    major: "Major",
    jobTitle: "Job Title",

    panelProfileTitle: "Profile",
    panelProfileDesc: "Avatar + nickname (hover to edit).",
    panelWorkTitle: "Work Info",
    panelWorkDesc: "School & job info (select to fill).",

    panelAccountTitle: "Account",
    panelAccountDesc: "Change password (verify current password).",
    currentPassword: "Current password",
    newPassword: "New password",
    confirmPassword: "Confirm new password",

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
    pwdWrong: "Current password is wrong",
    pwdFieldsRequired: "Please fill in all password fields",
    loadUserFail: "Unable to load user information. Please sign in again"
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

function rowSelect(key, label, valueHtml, options) {
  return `
    <div class="row-item" data-row="${key}">
      <div class="row-left">
        <div class="row-label">${label}</div>
        <div class="row-value" data-value>${valueHtml}</div>
      </div>
      <div class="row-actions">
        <a href="#" class="edit-link" data-action="edit">${t("edit")}</a>
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

    ${rowSelect("school", t("school"), escapeHtml(me?.school || "—"), [
      "清华大学", "北京大学", "复旦大学", "上海交通大学", "浙江大学", "南京大学", "中国科学技术大学", "哈尔滨工业大学", "西安交通大学", "同济大学"
    ])}
    ${rowSelect("major", t("major"), escapeHtml(me?.major || "—"), [
      "计算机科学", "教育学", "数学", "物理", "化学", "生物", "历史", "地理", "语文", "英语"
    ])}
    ${rowSelect("job_title", t("jobTitle"), escapeHtml(me?.job_title || "—"), [
      "教师", "教授", "讲师", "助教", "班主任", "教研员", "校长", "副校长", "主任", "副主任"
    ])}
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

    <div class="panel-actions">
      <a href="#" id="saveAccount" class="primary-link">${t("save")}</a>
    </div>
  `;

  document.getElementById("saveAccount").addEventListener("click", async (e) => {
    e.preventDefault();
    const curPwd = document.getElementById("curPwd").value.trim();
    const newPwd = document.getElementById("newPwd").value.trim();
    const confirmPwd = document.getElementById("confirmPwd").value.trim();

    if (!curPwd || !newPwd || !confirmPwd) {
      alert(t("pwdFieldsRequired"));
      return;
    }
    if (newPwd !== confirmPwd) {
      alert(t("pwdMismatch"));
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/api/user/change-password`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ current_password: curPwd, new_password: newPwd })
      });
      const data = await res.json();
      if (!res.ok || data.code !== 0) throw new Error(data.message || "Change password failed");

      alert(t("saveOk"));
      // 清空输入
      document.getElementById("curPwd").value = "";
      document.getElementById("newPwd").value = "";
      document.getElementById("confirmPwd").value = "";
    } catch (err) {
      console.error(err);
      alert(t("saveFail"));
    }
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
    const nextLocale = document.getElementById("langSelect").value;
    if (window.I18N) window.I18N.setLocale(nextLocale);
    else localStorage.setItem("locale", nextLocale);

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
  } else if (key === "school") {
    editorHtml = `
      <select class="inline-select" data-editor>
        <option value="">—</option>
        <option value="清华大学">清华大学</option>
        <option value="北京大学">北京大学</option>
        <option value="复旦大学">复旦大学</option>
        <option value="上海交通大学">上海交通大学</option>
        <option value="浙江大学">浙江大学</option>
        <option value="南京大学">南京大学</option>
        <option value="中国科学技术大学">中国科学技术大学</option>
        <option value="哈尔滨工业大学">哈尔滨工业大学</option>
        <option value="西安交通大学">西安交通大学</option>
        <option value="同济大学">同济大学</option>
      </select>
    `;
  } else if (key === "major") {
    editorHtml = `
      <select class="inline-select" data-editor>
        <option value="">—</option>
        <option value="计算机科学">计算机科学</option>
        <option value="教育学">教育学</option>
        <option value="数学">数学</option>
        <option value="物理">物理</option>
        <option value="化学">化学</option>
        <option value="生物">生物</option>
        <option value="历史">历史</option>
        <option value="地理">地理</option>
        <option value="语文">语文</option>
        <option value="英语">英语</option>
      </select>
    `;
  } else if (key === "job_title") {
    editorHtml = `
      <select class="inline-select" data-editor>
        <option value="">—</option>
        <option value="教师">教师</option>
        <option value="教授">教授</option>
        <option value="讲师">讲师</option>
        <option value="助教">助教</option>
        <option value="班主任">班主任</option>
        <option value="教研员">教研员</option>
        <option value="校长">校长</option>
        <option value="副校长">副校长</option>
        <option value="主任">主任</option>
        <option value="副主任">副主任</option>
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
    alert(t("loadUserFail"));
    me = {}; // 设置为空对象以显示默认内容
  }

  currentView = "profile";
  rerenderCurrent();
});
