const settingsDict = {
    zh: {
    pageTitle: "设置",
    settingsTitle: "偏好设置",
    langLabel: "语言",
    fontLabel: "字体大小",
    save: "保存设置SAVE",
    saved: "设置已保存",
    profile: "个人信息",
    classInfo: "班级信息",
    logout: "退出登录",
    small:"小", 
    medium:"中", 
    large:"大"
  },
  en: {
    pageTitle: "Settings",
    settingsTitle: "Preferences",
    langLabel: "Language",
    fontLabel: "Font size",
    save: "Save保存设置",
    saved: "Settings saved",
    profile: "Profile",
    classInfo: "Class Info",
    logout: "Sign out",
    small:"Small", 
    medium:"Medium", 
    large:"Large"
  }
};

function applySettingsLang() {
  const lang = localStorage.getItem("locale") || "zh";
  const t = settingsDict[lang];

  document.getElementById("pageTitle").textContent = t.pageTitle;
  document.getElementById("settingsTitle").textContent = t.settingsTitle;
  document.getElementById("langLabel").textContent = t.langLabel;
  document.getElementById("fontLabel").textContent = t.fontLabel;
  document.getElementById("saveBtn").textContent = t.save;
  document.querySelector("#fontSelect option[value='small']").textContent = t.small;
  document.querySelector("#fontSelect option[value='medium']").textContent = t.medium;
  document.querySelector("#fontSelect option[value='large']").textContent = t.large;

  // 顶栏系统名（可选）
  const appName = document.getElementById("appName");
  if (appName) appName.textContent = lang === "zh" ? "AI 辅助备课系统" : "AI Lesson Planner";
}

function initSettingsForm() {
  const lang = localStorage.getItem("locale") || "zh";
  const font = localStorage.getItem("font_size") || "medium";
  document.getElementById("langSelect").value = lang;
  document.getElementById("fontSelect").value = font;
}

function saveSettings() {
  const lang = document.getElementById("langSelect").value;
  const font = document.getElementById("fontSelect").value;

  localStorage.setItem("locale", lang);
  localStorage.setItem("font_size", font);

  // 立即生效
  if (typeof applySystemSettings === "function") applySystemSettings();

  // ✅ 关键：刷新侧边栏/顶栏语言
  if (typeof applyTeacherLang === "function") applyTeacherLang();

  // 刷新设置页自身文案
  applySettingsLang();

  alert(settingsDict[lang].saved);
}

document.addEventListener("DOMContentLoaded", () => {
  // 初始化文案 + 表单
  applySettingsLang();
  initSettingsForm();

  // ✅ 不用 onclick，避免 saveSettings not defined
  document.getElementById("saveBtn").addEventListener("click", (e) => {
    e.preventDefault();
    saveSettings();
  });
});
