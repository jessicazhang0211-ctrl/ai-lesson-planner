(function (global) {
  if (global.I18N) return;

  const dictionaries = {};
  const EVENT_NAME = "app:locale-changed";

  function normalizeLocale(locale) {
    return (locale || "zh").toLowerCase().startsWith("en") ? "en" : "zh";
  }

  function getLocale() {
    return normalizeLocale(global.localStorage.getItem("locale") || "zh");
  }

  function setLocale(locale) {
    const next = normalizeLocale(locale);
    const prev = getLocale();
    global.localStorage.setItem("locale", next);
    if (prev !== next) {
      global.dispatchEvent(new CustomEvent(EVENT_NAME, { detail: { locale: next } }));
      // Keep backward compatibility for existing listeners.
      global.dispatchEvent(new Event("cm_locale_changed"));
    }
    return next;
  }

  function registerDict(name, dict) {
    if (!name || !dict) return;
    dictionaries[name] = dict;
  }

  function resolveDict(dictOrName) {
    if (!dictOrName) return null;
    if (typeof dictOrName === "string") return dictionaries[dictOrName] || null;
    if (typeof dictOrName === "object") return dictOrName;
    return null;
  }

  function t(dictOrName, key, fallback) {
    const dict = resolveDict(dictOrName);
    if (!dict || !key) return fallback || key || "";
    const locale = getLocale();
    const byLocale = dict[locale] || dict.zh || {};
    if (Object.prototype.hasOwnProperty.call(byLocale, key)) return byLocale[key];
    const zh = dict.zh || {};
    if (Object.prototype.hasOwnProperty.call(zh, key)) return zh[key];
    return fallback || key;
  }

  function applyDataI18n(dictOrName, root) {
    const dict = resolveDict(dictOrName);
    if (!dict) return;
    const scope = root || document;
    const locale = getLocale();
    const byLocale = dict[locale] || dict.zh || {};

    scope.querySelectorAll("[data-i18n]").forEach((el) => {
      const key = el.getAttribute("data-i18n");
      if (key && Object.prototype.hasOwnProperty.call(byLocale, key)) {
        el.textContent = byLocale[key];
      }
    });

    scope.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
      const key = el.getAttribute("data-i18n-placeholder");
      if (key && Object.prototype.hasOwnProperty.call(byLocale, key)) {
        el.setAttribute("placeholder", byLocale[key]);
      }
    });

    scope.querySelectorAll("[data-i18n-title]").forEach((el) => {
      const key = el.getAttribute("data-i18n-title");
      if (key && Object.prototype.hasOwnProperty.call(byLocale, key)) {
        el.setAttribute("title", byLocale[key]);
      }
    });
  }

  function onLocaleChange(handler) {
    if (typeof handler !== "function") return function () {};
    const listener = (evt) => handler(evt.detail ? evt.detail.locale : getLocale());
    global.addEventListener(EVENT_NAME, listener);
    return function unsubscribe() {
      global.removeEventListener(EVENT_NAME, listener);
    };
  }

  global.I18N = {
    getLocale,
    setLocale,
    registerDict,
    t,
    applyDataI18n,
    onLocaleChange,
    eventName: EVENT_NAME
  };
})(window);
