function initSettings() {
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

  alert(lang === "zh" ? "设置已保存" : "Settings saved");

  // 返回教师主页
  window.location.href = "./index.html";
}

// ✅ 页面加载后绑定事件（不用 onclick）
document.addEventListener("DOMContentLoaded", () => {
  initSettings();
  document.getElementById("saveBtn").addEventListener("click", saveSettings);
});
