import {
  BookOpen,
  Brain,
  ClipboardCheck,
  Download,
  FileText,
  Library,
  Plus,
  Presentation,
  RefreshCw,
  Save,
  Search,
  Settings,
  ShieldCheck,
  Upload,
  Users
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { apiRequest } from "../../api/client.js";
import Button from "../../components/ui/Button.jsx";
import StatusPill from "../../components/ui/StatusPill.jsx";
import { useI18n } from "../../context/I18nContext.jsx";

const config = {
  lesson: { key: "lesson", icon: FileText, endpoint: "/api/lesson/history" },
  ppt: { key: "ppt", icon: Presentation },
  exercise: { key: "exercise", icon: ClipboardCheck, endpoint: "/api/exercise/history" },
  resource: { key: "resource", icon: Library, endpoint: "/api/resource/publish" },
  review: { key: "review", icon: ShieldCheck, endpoint: "/api/resource/review?status=pending_review" },
  knowledge: { key: "knowledge", icon: Brain, endpoint: "/api/resource/knowledge-items" },
  validation: { key: "validation", icon: ShieldCheck, endpoint: "/api/lesson/validation-logs" },
  class: { key: "classManagement", icon: Users, endpoint: "/api/class/?status=all" },
  settings: { key: "settings", icon: Settings }
};

function pickRows(payload) {
  if (Array.isArray(payload)) return payload;
  if (!payload || typeof payload !== "object") return [];
  return payload.items || payload.rows || payload.list || payload.classes || payload.logs || payload.submissions || payload.history || [];
}

export default function TeacherFeaturePage({ type }) {
  const { t } = useI18n();
  const page = config[type] || config.lesson;
  const Icon = page.icon || BookOpen;
  const [rows, setRows] = useState([]);
  const [status, setStatus] = useState("idle");
  const title = t(page.key);

  const actions = useMemo(() => {
    if (type === "settings") return [{ label: t("save"), icon: Save, primary: true }];
    if (type === "knowledge") return [{ label: t("refresh"), icon: RefreshCw }, { label: t("upload"), icon: Upload, primary: true }];
    if (type === "class") return [{ label: t("refresh"), icon: RefreshCw }, { label: t("signUp"), icon: Plus, primary: true }];
    return [{ label: t("refresh"), icon: RefreshCw }, { label: t("exportOverview"), icon: Download, primary: true }];
  }, [t, type]);

  async function load() {
    if (!page.endpoint) return;
    setStatus("loading");
    try {
      const payload = await apiRequest(page.endpoint);
      setRows(pickRows(payload));
      setStatus("ready");
    } catch {
      setRows([]);
      setStatus("failed");
    }
  }

  useEffect(() => {
    load();
  }, [type]);

  return (
    <div className="page-stack">
      <section className="page-heading">
        <div className="title-with-icon">
          <span className="title-icon"><Icon size={22} /></span>
          <div>
            <h1>{title}</h1>
            <p>{status === "loading" ? t("loading") : t("classOverview")}</p>
          </div>
        </div>
        <div className="heading-actions">
          {actions.map((action) => (
            <Button
              key={action.label}
              icon={action.icon}
              variant={action.primary ? "primary" : "default"}
              onClick={action.label === t("refresh") ? load : undefined}
            >
              {action.label}
            </Button>
          ))}
        </div>
      </section>

      {status === "failed" ? <div className="notice error">{t("loadFailed")}</div> : null}

      <section className="content-grid two">
        <article className="panel">
          <div className="panel-head">
            <div>
              <h2>{title}</h2>
              <p>{rows.length ? `${rows.length}` : t("noData")}</p>
            </div>
            <div className="search-box">
              <Search size={15} />
              <input aria-label="search" />
            </div>
          </div>
          <div className="list">
            {rows.slice(0, 8).map((row, index) => (
              <div className="list-row split" key={row.id || row.log_id || `${type}-${index}`}>
                <div>
                  <strong>{row.title || row.name || row.class_name || row.resource_title || row.message || `${title} ${index + 1}`}</strong>
                  <small>{row.created_at || row.updated_at || row.status || row.type || ""}</small>
                </div>
                <StatusPill tone={row.status === "failed" ? "danger" : row.status === "completed" ? "success" : "neutral"}>
                  {row.status || row.role || row.resource_type || "ok"}
                </StatusPill>
              </div>
            ))}
            {!rows.length ? <div className="empty-state">{status === "loading" ? t("loading") : t("noData")}</div> : null}
          </div>
        </article>

        <article className="panel tool-panel">
          <div className="panel-head">
            <div>
              <h2>{t("settings")}</h2>
              <p>{title}</p>
            </div>
          </div>
          <div className="form-grid">
            <label>
              <span>{t("name")}</span>
              <input />
            </label>
            <label>
              <span>{t("classManagement")}</span>
              <select defaultValue="">
                <option value="">{t("noData")}</option>
              </select>
            </label>
            <label className="wide">
              <span>{t("suggestion")}</span>
              <textarea rows="7" />
            </label>
            <Button icon={Save} variant="primary">{t("save")}</Button>
          </div>
        </article>
      </section>
    </div>
  );
}
