const studentSettingsDict = {
  zh: {
    pageTitle: "学生设置 · AI 辅助备课系统",
    pageHeading: "设置",
    accountSettingsTitle: "账号设置",
    accountSettingsSub: "学生仅可修改头像、签名与登录密码",
    sectionPersonal: "个人信息",
    sectionGeneral: "通用",
    itemProfile: "个人资料",
    itemAccount: "账号安全",
    itemLanguage: "语言设置",
    profilePanelTitle: "个人资料",
    profilePanelDesc: "可更新头像和个性签名。",
    accountPanelTitle: "账号安全",
    accountPanelDesc: "修改登录密码需先验证当前密码。",
    languagePanelTitle: "语言设置",
    languagePanelDesc: "修改后将同步整个学生端界面语言。",
    languageLabel: "界面语言",
    languageZh: "简体中文",
    languageEn: "English",
    avatarLabel: "头像",
    signatureLabel: "签名",
    signaturePlaceholder: "写一句学习目标或鼓励自己的话",
    passwordLabel: "修改密码",
    passwordOldPlaceholder: "当前密码",
    passwordNewPlaceholder: "新密码",
    passwordConfirmPlaceholder: "确认新密码",
    btnReset: "重置",
    btnSave: "保存设置",
    forcePasswordTip: "检测到你正在使用初始密码，请先完成改密。",
    currentPwdRequired: "请输入当前密码",
    pwdChangeFailed: "修改密码失败",
    pwdMismatch: "两次输入的新密码不一致",
    saved: "设置已保存"
  },
  en: {
    pageTitle: "Student Settings · AI Lesson Planner",
    pageHeading: "Settings",
    accountSettingsTitle: "Account Settings",
    accountSettingsSub: "Students can only update avatar, signature, and login password",
    sectionPersonal: "Personal",
    sectionGeneral: "General",
    itemProfile: "Profile",
    itemAccount: "Account Security",
    itemLanguage: "Language",
    profilePanelTitle: "Profile",
    profilePanelDesc: "Update your avatar and personal signature.",
    accountPanelTitle: "Account Security",
    accountPanelDesc: "Changing password requires your current password.",
    languagePanelTitle: "Language",
    languagePanelDesc: "Changes will apply across the student portal.",
    languageLabel: "Interface Language",
    languageZh: "Simplified Chinese",
    languageEn: "English",
    avatarLabel: "Avatar",
    signatureLabel: "Signature",
    signaturePlaceholder: "Write a learning goal or a message to motivate yourself",
    passwordLabel: "Change Password",
    passwordOldPlaceholder: "Current password",
    passwordNewPlaceholder: "New password",
    passwordConfirmPlaceholder: "Confirm new password",
    btnReset: "Reset",
    btnSave: "Save Settings",
    forcePasswordTip: "You are using the initial password. Please change it first.",
    currentPwdRequired: "Please enter current password",
    pwdChangeFailed: "Failed to change password",
    pwdMismatch: "The two new passwords do not match",
    saved: "Settings saved"
  }
};
const i18n = window.I18N || null;
if (i18n) i18n.registerDict("studentSettings", studentSettingsDict);

function getLocale() {
  return i18n ? i18n.getLocale() : (localStorage.getItem("locale") || "zh");
}

function t(key) {
  if (i18n) return i18n.t("studentSettings", key, key);
  const locale = getLocale();
  return (studentSettingsDict[locale] && studentSettingsDict[locale][key]) || studentSettingsDict.zh[key] || key;
}

function applyPageI18n() {
  if (i18n) i18n.applyDataI18n("studentSettings", document);
  document.title = t("pageTitle");
  const languageSelect = document.getElementById("languageSelect");
  if (languageSelect) {
    languageSelect.value = getLocale();
  }
}

function getCurrentUserId() {
  try {
    const user = JSON.parse(localStorage.getItem("login_user") || "{}");
    return user.id || user.user_id || "";
  } catch {
    return "";
  }
}

async function changePassword(currentPassword, newPassword) {
  const uid = String(getCurrentUserId() || "");
  const token = localStorage.getItem("auth_token") || "";
  const res = await fetch("http://127.0.0.1:5000/api/user/change-password", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(uid ? { "X-User-Id": uid } : {}),
      ...(token ? { "Authorization": `Bearer ${token}` } : {})
    },
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword
    })
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.code !== 0) {
    throw new Error(data.message || t("pwdChangeFailed"));
  }
}

function loadSettings() {
  const signature = localStorage.getItem("student_signature") || "";
  const avatar = localStorage.getItem("student_avatar") || "";
  const signatureInput = document.getElementById("signatureInput");
  const avatarPreview = document.getElementById("avatarPreview");
  if (signatureInput) signatureInput.value = signature;
  if (avatar && avatarPreview) avatarPreview.src = avatar;
}

function bindSettingsViewSwitch() {
  const navItems = Array.from(document.querySelectorAll(".settings-nav-item"));
  const panels = Array.from(document.querySelectorAll(".settings-view-panel"));
  if (!navItems.length || !panels.length) return;

  const activateView = (view) => {
    navItems.forEach((item) => {
      item.classList.toggle("active", item.dataset.view === view);
    });
    panels.forEach((panel) => {
      panel.classList.toggle("active", panel.dataset.panel === view);
    });
  };

  navItems.forEach((item) => {
    item.addEventListener("click", (e) => {
      e.preventDefault();
      activateView(item.dataset.view || "profile");
    });
  });

  activateView("profile");
}

function bindSettingsEvents() {
  const languageSelect = document.getElementById("languageSelect");
  languageSelect?.addEventListener("change", (e) => {
    const nextLocale = String(e.target.value || "zh");
    if (i18n) i18n.setLocale(nextLocale);
    else localStorage.setItem("locale", nextLocale);
    applyPageI18n();
  });

  const avatarInput = document.getElementById("avatarInput");
  avatarInput?.addEventListener("change", (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const url = String(reader.result || "");
      localStorage.setItem("student_avatar", url);
      const preview = document.getElementById("avatarPreview");
      const topAvatar = document.getElementById("studentAvatar");
      if (preview) preview.src = url;
      if (topAvatar) topAvatar.src = url;
    };
    reader.readAsDataURL(file);
  });

  document.getElementById("btnReset")?.addEventListener("click", () => {
    document.getElementById("signatureInput").value = "";
    document.getElementById("passwordOld").value = "";
    document.getElementById("passwordNew").value = "";
    document.getElementById("passwordConfirm").value = "";
  });

  document.getElementById("btnSave")?.addEventListener("click", () => {
    const signature = document.getElementById("signatureInput").value.trim();
    localStorage.setItem("student_signature", signature);

    const oldPwd = document.getElementById("passwordOld").value;
    const newPwd = document.getElementById("passwordNew").value;
    const confirmPwd = document.getElementById("passwordConfirm").value;
    const hasPwdInput = oldPwd || newPwd || confirmPwd;
    const saveFlow = async () => {
      if (hasPwdInput) {
        if (!oldPwd) {
          alert(t("currentPwdRequired"));
          return;
        }
        if (newPwd !== confirmPwd) {
          alert(t("pwdMismatch"));
          return;
        }
        try {
          await changePassword(oldPwd, newPwd);
          localStorage.removeItem("must_change_password");
        } catch (e) {
          alert(String(e.message || t("pwdChangeFailed")));
          return;
        }
      }
      alert(t("saved"));
    };

    saveFlow();
  });
}

function maybeShowForcePasswordNotice() {
  const forceByQuery = new URLSearchParams(window.location.search).get("force_password") === "1";
  const forceByStorage = localStorage.getItem("must_change_password") === "1";
  if (forceByQuery || forceByStorage) {
    alert(t("forcePasswordTip"));
  }
}

document.addEventListener("DOMContentLoaded", () => {
  applySystemSettings();
  loadStudentProfile();
  applyPageI18n();
  loadSettings();
  bindSettingsViewSwitch();
  bindSettingsEvents();
  maybeShowForcePasswordNotice();
  if (i18n) {
    i18n.onLocaleChange(() => {
      applyPageI18n();
    });
  }
});
