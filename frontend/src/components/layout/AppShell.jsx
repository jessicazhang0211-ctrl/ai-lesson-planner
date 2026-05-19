import {
  BarChart3,
  BookOpen,
  Brain,
  ClipboardCheck,
  FileText,
  GraduationCap,
  Home,
  Library,
  LogOut,
  Menu,
  Presentation,
  Settings,
  ShieldCheck,
  UserRound,
  Users
} from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext.jsx";
import { useI18n } from "../../context/I18nContext.jsx";
import { logoUrl } from "../../utils/assets.js";
import Button from "../ui/Button.jsx";

const teacherNav = [
  { to: "/teacher", key: "dashboard", icon: BarChart3 },
  { to: "/teacher/lesson", key: "lesson", icon: FileText },
  { to: "/teacher/ppt", key: "ppt", icon: Presentation },
  { to: "/teacher/exercise", key: "exercise", icon: ClipboardCheck },
  { to: "/teacher/resource", key: "resource", icon: Library },
  { to: "/teacher/review", key: "review", icon: ShieldCheck },
  { to: "/teacher/knowledge", key: "knowledge", icon: Brain },
  { to: "/teacher/validation", key: "validation", icon: ShieldCheck },
  { to: "/teacher/class", key: "classManagement", icon: Users },
  { to: "/teacher/settings", key: "settings", icon: Settings }
];

const studentNav = [
  { to: "/student", key: "overview", icon: Home },
  { to: "/student/practice", key: "practice", icon: ClipboardCheck },
  { to: "/student/review", key: "review", icon: ShieldCheck },
  { to: "/student/lessons", key: "lessons", icon: BookOpen },
  { to: "/student/scores", key: "scores", icon: BarChart3 },
  { to: "/student/settings", key: "settings", icon: Settings }
];

export default function AppShell({ audience }) {
  const [collapsed, setCollapsed] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const { user, signOut } = useAuth();
  const { t, locale, setLocale } = useI18n();
  const navigate = useNavigate();
  const nav = audience === "student" ? studentNav : teacherNav;
  const home = audience === "student" ? "/student" : "/teacher";

  function logout() {
    signOut();
    navigate(audience === "student" ? "/student/login" : "/login", { replace: true });
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <button className="brand-button" type="button" onClick={() => navigate(home)} aria-label={t("appName")}>
          <img src={logoUrl} alt="" className="brand-logo" />
          <span className="brand-name">{t("appName")}</span>
        </button>

        <div className="topbar-actions">
          <Button
            variant="ghost-dark"
            icon={GraduationCap}
            onClick={() => setLocale(locale === "zh" ? "en" : "zh")}
            aria-label={t("language")}
          >
            {locale === "zh" ? "EN" : "ZH"}
          </Button>
          <div className="user-menu-wrap">
            <button className="user-button" type="button" onClick={() => setMenuOpen((open) => !open)}>
              <UserRound size={18} />
              <span>{user?.nickname || user?.name || user?.email || user?.stu_id || "User"}</span>
            </button>
            {menuOpen ? (
              <div className="user-menu">
                <button type="button" onClick={() => navigate(`${home}/settings`)}>
                  <Settings size={15} />
                  <span>{t("settings")}</span>
                </button>
                <button type="button" className="danger" onClick={logout}>
                  <LogOut size={15} />
                  <span>{t("signOut")}</span>
                </button>
              </div>
            ) : null}
          </div>
        </div>
      </header>

      <div className="shell-body">
        <aside className={`sidebar ${collapsed ? "collapsed" : ""}`}>
          <button className="sidebar-toggle" type="button" onClick={() => setCollapsed((value) => !value)}>
            <Menu size={18} />
          </button>
          <nav className="side-nav" aria-label={audience === "student" ? t("studentPortal") : t("teacherPortal")}>
            {nav.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink key={item.to} to={item.to} end={item.to === home} className="side-link">
                  <Icon size={17} />
                  <span>{t(item.key)}</span>
                </NavLink>
              );
            })}
          </nav>
        </aside>

        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
