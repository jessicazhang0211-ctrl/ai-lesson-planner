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
        alert("两次输入的新密码不一致");
        return;
      }
      localStorage.setItem("student_password", newPwd);
    }
    alert("设置已保存");
  });
}

document.addEventListener("DOMContentLoaded", () => {
  loadSettings();
  bindSettingsEvents();
});
