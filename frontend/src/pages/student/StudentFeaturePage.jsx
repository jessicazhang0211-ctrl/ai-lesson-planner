import { ArrowRight, BookOpen, ClipboardCheck, RefreshCw, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { apiRequest } from "../../api/client.js";
import Button from "../../components/ui/Button.jsx";
import StatusPill from "../../components/ui/StatusPill.jsx";
import { useI18n } from "../../context/I18nContext.jsx";

const pages = {
  practice: { key: "practice", icon: ClipboardCheck, endpoint: "/api/student/assignments" },
  practiceDo: { key: "practice", icon: ClipboardCheck },
  review: { key: "review", icon: ShieldCheck, endpoint: "/api/student/assignments" },
  lessons: { key: "lessons", icon: BookOpen, endpoint: "/api/student/lessons" },
  scores: { key: "scores", icon: ShieldCheck, endpoint: "/api/student/scores" }
};

function normalize(payload) {
  if (Array.isArray(payload)) return payload;
  if (!payload || typeof payload !== "object") return [];
  return payload.assignments || payload.items || payload.list || payload.rows || payload.lessons || payload.scores || [];
}

export default function StudentFeaturePage({ type }) {
  const { t } = useI18n();
  const page = pages[type] || pages.practice;
  const Icon = page.icon;
  const location = useLocation();
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [status, setStatus] = useState("idle");
  const title = t(page.key);
  const publishId = new URLSearchParams(location.search).get("publish_id");

  async function load() {
    if (type === "practiceDo" && publishId) {
      setStatus("loading");
      try {
        const payload = await apiRequest(`/api/student/exercises/${publishId}`);
        setItems(normalize(payload.exercises || payload.items || payload));
        setStatus("ready");
      } catch {
        setStatus("failed");
      }
      return;
    }

    if (!page.endpoint) return;
    setStatus("loading");
    try {
      const payload = await apiRequest(page.endpoint);
      setItems(normalize(payload));
      setStatus("ready");
    } catch {
      setItems([]);
      setStatus("failed");
    }
  }

  useEffect(() => {
    load();
  }, [type, publishId]);

  return (
    <div className="page-stack">
      <section className="page-heading">
        <div className="title-with-icon">
          <span className="title-icon"><Icon size={22} /></span>
          <div>
            <h1>{title}</h1>
            <p>{status === "loading" ? t("loading") : t("overview")}</p>
          </div>
        </div>
        <div className="heading-actions">
          <Button icon={RefreshCw} onClick={load}>{t("refresh")}</Button>
        </div>
      </section>

      {status === "failed" ? <div className="notice error">{t("loadFailed")}</div> : null}

      <section className="panel">
        <div className="panel-head">
          <div>
            <h2>{title}</h2>
            <p>{items.length ? `${items.length}` : t("noData")}</p>
          </div>
        </div>
        <div className="list">
          {items.map((item, index) => (
            <div className="list-row split" key={item.id || item.publish_id || `${type}-${index}`}>
              <div>
                <strong>{item.title || item.name || item.question || `${title} ${index + 1}`}</strong>
                <small>{item.created_at || item.status || item.score || ""}</small>
              </div>
              {type === "practice" ? (
                <Button icon={ArrowRight} onClick={() => navigate(`/student/practice-do?publish_id=${item.publish_id || item.id || ""}`)}>
                  {t("start")}
                </Button>
              ) : (
                <StatusPill tone={item.status === "completed" ? "success" : "neutral"}>{item.status || "ok"}</StatusPill>
              )}
            </div>
          ))}
          {!items.length ? <div className="empty-state">{status === "loading" ? t("loading") : t("noData")}</div> : null}
        </div>
      </section>
    </div>
  );
}
