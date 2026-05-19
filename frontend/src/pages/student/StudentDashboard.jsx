import { ArrowRight, RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiRequest } from "../../api/client.js";
import Button from "../../components/ui/Button.jsx";
import StatCard from "../../components/ui/StatCard.jsx";
import StatusPill from "../../components/ui/StatusPill.jsx";
import { useI18n } from "../../context/I18nContext.jsx";

function normalizeAssignments(payload) {
  if (Array.isArray(payload)) return payload;
  if (!payload || typeof payload !== "object") return [];
  return payload.assignments || payload.items || payload.list || payload.rows || [];
}

export default function StudentDashboard() {
  const { t, locale } = useI18n();
  const navigate = useNavigate();
  const [assignments, setAssignments] = useState([]);
  const [overview, setOverview] = useState({});
  const [status, setStatus] = useState("idle");

  const tasks = useMemo(() => assignments.filter((item) => item.status !== "completed").slice(0, 6), [assignments]);
  const analysis = overview.analysis || {};

  const stats = [
    { label: t("todoAssignments"), value: overview.todo ?? tasks.length ?? 0, hint: t("pending") },
    { label: t("practiceThisWeek"), value: overview.completed ?? 0, hint: t("practice") },
    { label: t("accuracy"), value: overview.avg_score != null ? `${overview.avg_score}%` : "--", hint: t("weeklyTrend") },
    { label: t("latestScore"), value: overview.latest_score ?? "--", hint: t("scores") }
  ];

  async function load() {
    setStatus("loading");
    try {
      const [assignmentPayload, overviewPayload] = await Promise.all([
        apiRequest("/api/student/assignments"),
        apiRequest(`/api/student/overview?lang=${encodeURIComponent(locale)}`)
      ]);
      setAssignments(normalizeAssignments(assignmentPayload));
      setOverview(overviewPayload || {});
      setStatus("ready");
    } catch {
      setAssignments([]);
      setOverview({});
      setStatus("failed");
    }
  }

  useEffect(() => {
    load();
  }, [locale]);

  return (
    <div className="page-stack">
      <section className="student-hero">
        <div>
          <h1>{t("overview")}</h1>
          <p>{t("learningInsights")}</p>
        </div>
        <div className="heading-actions">
          <Button icon={RefreshCw} onClick={load}>{t("refresh")}</Button>
          <Button icon={ArrowRight} variant="primary" onClick={() => navigate("/student/practice")}>{t("start")}</Button>
        </div>
      </section>

      {status === "failed" ? <div className="notice error">{t("loadFailed")}</div> : null}

      <section className="stat-grid">
        {stats.map((item) => <StatCard key={item.label} {...item} />)}
      </section>

      <section className="content-grid two">
        <article className="panel">
          <div className="panel-head">
            <div>
              <h2>{t("todoAssignments")}</h2>
              <p>{tasks.length} {t("pending")}</p>
            </div>
          </div>
          <div className="list">
            {tasks.map((item) => (
              <div className="list-row split" key={item.publish_id || item.id || item.title}>
                <div>
                  <strong>{item.title || t("exercise")}</strong>
                  <small>{item.created_at || item.published_at || ""}</small>
                </div>
                <Button icon={ArrowRight} onClick={() => navigate(`/student/practice-do?publish_id=${item.publish_id || item.id || ""}`)}>
                  {t("start")}
                </Button>
              </div>
            ))}
            {!tasks.length ? <div className="empty-state">{status === "loading" ? t("loading") : t("noData")}</div> : null}
          </div>
        </article>

        <article className="panel">
          <div className="panel-head">
            <div>
              <h2>{t("learningInsights")}</h2>
              <p>{t("suggestion")}</p>
            </div>
          </div>
          <div className="insight-grid">
            <div>
              <span>{t("weakSpot")}</span>
              <strong>{analysis.weak_spot || "--"}</strong>
            </div>
            <div>
              <span>{t("studyState")}</span>
              <strong>{analysis.study_state || "--"}</strong>
            </div>
            <div className="wide">
              <span>{t("suggestion")}</span>
              <strong>{analysis.study_tip || "--"}</strong>
            </div>
          </div>
        </article>
      </section>

      <section className="panel">
        <div className="panel-head">
          <div>
            <h2>{t("practice")}</h2>
            <p>{t("scores")}</p>
          </div>
        </div>
        <div className="list horizontal">
          {assignments.slice(0, 5).map((item) => (
            <div className="mini-card" key={item.publish_id || item.id || item.title}>
              <strong>{item.title || t("exercise")}</strong>
              <StatusPill tone={item.status === "completed" ? "success" : "warn"}>{item.status || t("pending")}</StatusPill>
            </div>
          ))}
          {!assignments.length ? <div className="empty-state">{t("noData")}</div> : null}
        </div>
      </section>
    </div>
  );
}
