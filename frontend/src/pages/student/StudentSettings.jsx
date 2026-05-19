import { Save } from "lucide-react";
import { useState } from "react";
import { apiRequest } from "../../api/client.js";
import Button from "../../components/ui/Button.jsx";
import { useI18n } from "../../context/I18nContext.jsx";

export default function StudentSettings() {
  const { t, locale, setLocale } = useI18n();
  const [fontSize, setFontSize] = useState(() => localStorage.getItem("font_size") || "medium");
  const [passwords, setPasswords] = useState({ current: "", next: "", confirm: "" });
  const [message, setMessage] = useState("");

  async function savePreferences() {
    localStorage.setItem("font_size", fontSize);
    document.documentElement.dataset.font = fontSize;
    setMessage(t("saved"));
  }

  async function changePassword(event) {
    event.preventDefault();
    setMessage("");
    if (!passwords.current || !passwords.next || !passwords.confirm) return setMessage(t("required"));
    if (passwords.next !== passwords.confirm) return setMessage(t("passwordMismatch"));
    try {
      await apiRequest("/api/user/change-password", {
        method: "POST",
        body: {
          current_password: passwords.current,
          new_password: passwords.next
        }
      });
      localStorage.removeItem("must_change_password");
      setPasswords({ current: "", next: "", confirm: "" });
      setMessage(t("saved"));
    } catch (err) {
      setMessage(err?.message || t("loadFailed"));
    }
  }

  return (
    <div className="page-stack">
      <section className="page-heading">
        <div>
          <h1>{t("settings")}</h1>
          <p>{t("studentPortal")}</p>
        </div>
      </section>

      {message ? <div className="notice">{message}</div> : null}

      <section className="content-grid two">
        <article className="panel">
          <div className="panel-head">
            <div>
              <h2>{t("settings")}</h2>
              <p>{t("language")} / {t("fontSize")}</p>
            </div>
          </div>
          <div className="form-grid">
            <label>
              <span>{t("language")}</span>
              <select value={locale} onChange={(event) => setLocale(event.target.value)}>
                <option value="zh">中文</option>
                <option value="en">English</option>
              </select>
            </label>
            <label>
              <span>{t("fontSize")}</span>
              <select value={fontSize} onChange={(event) => setFontSize(event.target.value)}>
                <option value="small">{t("small")}</option>
                <option value="medium">{t("medium")}</option>
                <option value="large">{t("large")}</option>
              </select>
            </label>
            <Button icon={Save} variant="primary" onClick={savePreferences}>{t("save")}</Button>
          </div>
        </article>

        <article className="panel">
          <div className="panel-head">
            <div>
              <h2>{t("changePassword")}</h2>
              <p>{t("studentPortal")}</p>
            </div>
          </div>
          <form className="form-grid" onSubmit={changePassword}>
            <label>
              <span>{t("currentPassword")}</span>
              <input type="password" value={passwords.current} onChange={(event) => setPasswords((prev) => ({ ...prev, current: event.target.value }))} />
            </label>
            <label>
              <span>{t("newPassword")}</span>
              <input type="password" value={passwords.next} onChange={(event) => setPasswords((prev) => ({ ...prev, next: event.target.value }))} />
            </label>
            <label>
              <span>{t("confirmPassword")}</span>
              <input type="password" value={passwords.confirm} onChange={(event) => setPasswords((prev) => ({ ...prev, confirm: event.target.value }))} />
            </label>
            <Button type="submit" icon={Save} variant="primary">{t("save")}</Button>
          </form>
        </article>
      </section>
    </div>
  );
}
