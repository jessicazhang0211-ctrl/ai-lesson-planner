const studentSettingsDict = {
  zh: {
    pwdMismatch: "两次输入的新密码不一致",
    saved: "设置已保存"
  },
  en: {
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

function loadSettings() {
  const signature = localStorage.getItem("student_signature") || "";
  const avatar = localStorage.getItem("student_avatar") || "";
  const signatureInput = document.getElementById("signatureInput");
  const avatarPreview = document.getElementById("avatarPreview");
  if (signatureInput) signatureInput.value = signature;
  if (avatar && avatarPreview) avatarPreview.src = avatar;
}

function bindSettingsEvents() {
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

    const newPwd = document.getElementById("passwordNew").value;
    const confirmPwd = document.getElementById("passwordConfirm").value;
    if (newPwd || confirmPwd) {
      if (newPwd !== confirmPwd) {
        alert(t("pwdMismatch"));
        return;
      }
      localStorage.setItem("student_password", newPwd);
    }
    alert(t("saved"));
  });
}

document.addEventListener("DOMContentLoaded", () => {
  loadSettings();
  bindSettingsEvents();
});
