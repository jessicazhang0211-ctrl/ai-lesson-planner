import { ArrowRight, Languages } from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { loginStudent, loginTeacher, registerTeacher } from "../../api/auth.js";
import Button from "../../components/ui/Button.jsx";
import { useAuth } from "../../context/AuthContext.jsx";
import { useI18n } from "../../context/I18nContext.jsx";
import { backgroundUrl, logoUrl } from "../../utils/assets.js";

function isValidEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

export default function AuthPage({ audience, mode }) {
  const { signIn } = useAuth();
  const { t, locale, setLocale } = useI18n();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    name: "",
    email: localStorage.getItem("prefill_email") || "",
    stuId: localStorage.getItem("prefill_stu_id") || "",
    password: "",
    confirm: ""
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const isStudent = audience === "student";
  const isRegister = mode === "register";
  const title = useMemo(() => {
    if (isStudent && isRegister) return `${t("studentPortal")} ${t("signUp")}`;
    if (isStudent) return `${t("studentPortal")} ${t("signIn")}`;
    return isRegister ? t("signUp") : t("signIn");
  }, [isRegister, isStudent, t]);

  function update(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function onSubmit(event) {
    event.preventDefault();
    setError("");

    if (isStudent && isRegister) {
      setError(t("studentSignupDisabled"));
      return;
    }

    if (isRegister) {
      if (!form.name || !form.email || !form.password || !form.confirm) return setError(t("required"));
      if (!isValidEmail(form.email)) return setError(t("invalidEmail"));
      if (form.password.length < 6) return setError(t("passwordTooShort"));
      if (form.password !== form.confirm) return setError(t("passwordMismatch"));
    } else if (isStudent) {
      if (!form.stuId || !form.password) return setError(t("required"));
    } else {
      if (!form.email || !form.password) return setError(t("required"));
      if (!isValidEmail(form.email)) return setError(t("invalidEmail"));
    }

    try {
      setBusy(true);
      if (isRegister) {
        await registerTeacher({ name: form.name, email: form.email, password: form.password });
        localStorage.setItem("prefill_email", form.email);
        navigate("/login", { replace: true, state: { notice: t("registerSuccess") } });
        return;
      }

      const data = isStudent
        ? await loginStudent({ stuId: form.stuId, password: form.password })
        : await loginTeacher({ email: form.email, password: form.password });

      signIn(data, isStudent ? "student" : "teacher");
      if (isStudent) {
        localStorage.setItem("prefill_stu_id", form.stuId);
        if (data?.must_change_password) localStorage.setItem("must_change_password", "1");
        else localStorage.removeItem("must_change_password");
        navigate(data?.must_change_password ? "/student/settings?force_password=1" : "/student", { replace: true });
      } else {
        localStorage.setItem("prefill_email", form.email);
        navigate("/teacher", { replace: true });
      }
    } catch (err) {
      setError(err?.message || t("loginFailed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-page" style={{ "--auth-bg": `url(${backgroundUrl})` }}>
      <Link className="portal-switch left" to={isStudent ? "/login" : "/student/login"}>
        {isStudent ? t("teacherPortal") : t("studentPortal")}
      </Link>
      <button className="portal-switch right" type="button" onClick={() => setLocale(locale === "zh" ? "en" : "zh")}>
        <Languages size={15} />
        <span>{locale === "zh" ? "EN" : "ZH"}</span>
      </button>

      <section className="auth-card" aria-labelledby="auth-title">
        <img src={logoUrl} className="auth-logo" alt="" />
        <div className="auth-heading">
          <div className="auth-brand">{t("appName")}</div>
          <h1 id="auth-title">{title}</h1>
        </div>

        <form className="auth-form" onSubmit={onSubmit}>
          {isRegister && !isStudent ? (
            <label>
              <span>{t("name")}</span>
              <input value={form.name} onChange={(event) => update("name", event.target.value)} autoComplete="name" />
            </label>
          ) : null}

          {isStudent && !isRegister ? (
            <label>
              <span>{t("studentId")}</span>
              <input value={form.stuId} onChange={(event) => update("stuId", event.target.value)} autoComplete="username" />
            </label>
          ) : null}

          {(!isStudent || (isStudent && isRegister)) ? (
            <label>
              <span>{t("email")}</span>
              <input value={form.email} onChange={(event) => update("email", event.target.value)} autoComplete="email" />
            </label>
          ) : null}

          <label>
            <span>{t("password")}</span>
            <input
              value={form.password}
              onChange={(event) => update("password", event.target.value)}
              type="password"
              autoComplete={isRegister ? "new-password" : "current-password"}
            />
          </label>

          {isRegister && !isStudent ? (
            <label>
              <span>{t("confirmPassword")}</span>
              <input value={form.confirm} onChange={(event) => update("confirm", event.target.value)} type="password" autoComplete="new-password" />
            </label>
          ) : null}

          {isStudent && isRegister ? <p className="auth-note">{t("studentSignupDisabled")}</p> : null}
          {error ? <p className="form-error">{error}</p> : null}

          <Button type="submit" variant="primary" icon={ArrowRight} disabled={busy || (isStudent && isRegister)}>
            {busy ? t("loading") : isRegister ? t("signUp") : t("signIn")}
          </Button>
        </form>

        <div className="auth-links">
          {isRegister ? (
            <Link to={isStudent ? "/student/login" : "/login"}>{t("goToLogin")}</Link>
          ) : (
            <Link to={isStudent ? "/student/register" : "/register"}>{t("goToRegister")}</Link>
          )}
        </div>
      </section>
    </div>
  );
}
