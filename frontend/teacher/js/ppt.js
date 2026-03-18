const pptDict = {
  zh: {
    title: "PPT 生成",
    sub: "该功能待完成，目前只是一个设想。",
    descTitle: "功能说明",
    descBody: "这里将来会提供 PPT 模板选择、内容生成与一键导出功能。当前版本仅保留入口，后续会逐步完善。"
  },
  en: {
    title: "PPT Generator",
    sub: "This feature is under construction and currently serves as an entry point.",
    descTitle: "Feature Notes",
    descBody: "Future updates will include template selection, content generation, and one-click export. The current version keeps the page entry and foundation only."
  }
};

function getPptLocale() {
  return localStorage.getItem("locale") || "zh";
}

function applyPptLang() {
  const locale = getPptLocale();
  const dict = pptDict[locale] || pptDict.zh;
  document.querySelectorAll("[data-ppt-i18n]").forEach((el) => {
    const key = el.getAttribute("data-ppt-i18n");
    if (dict[key]) {
      el.textContent = dict[key];
    }
  });
}

window.addEventListener("app:locale-changed", applyPptLang);
document.addEventListener("DOMContentLoaded", applyPptLang);
