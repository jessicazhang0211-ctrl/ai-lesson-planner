import { Download, RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { apiRequest } from "../../api/client.js";
import Button from "../../components/ui/Button.jsx";
import StatCard from "../../components/ui/StatCard.jsx";
import StatusPill from "../../components/ui/StatusPill.jsx";
import { useI18n } from "../../context/I18nContext.jsx";

const emptyOverview = {
  classes: [],
  monthly: [],
  weekly: [],
  praises: [],
  teacherAdvice: [],
  overview: { students: 0, active: 0, submitRate: 0, accuracyAvg: 0, risk: 0 }
};

function rate(part, total) {
  if (!total) return 0;
  return Math.round((Number(part || 0) / Number(total || 0)) * 100);
}

function BarSet({ items }) {
  if (!items?.length) return <div className="empty-state">--</div>;
  return (
    <div className="bar-chart">
      {items.slice(-8).map((item, index) => {
        const submit = Math.min(100, Math.max(0, Number(item.submit || 0)));
        const accuracy = Math.min(100, Math.max(0, Number(item.accuracy || 0)));
        return (
          <div className="bar-group" key={`${item.day || "day"}-${index}`}>
            <div className="bars">
              <span className="bar submit" style={{ height: `${submit}%` }} />
              <span className="bar accuracy" style={{ height: `${accuracy}%` }} />
            </div>
            <span className="bar-label">{item.day || index + 1}</span>
          </div>
        );
      })}
    </div>
  );
}

export default function TeacherDashboard() {
  const { t, locale } = useI18n();
  const [data, setData] = useState(emptyOverview);
  const [status, setStatus] = useState("idle");

  const overview = data.overview || emptyOverview.overview;
  const classes = data.classes || [];
  const advice = data.teacherAdvice || [];
  const praises = data.praises || [];

  const stats = useMemo(() => [
    { label: t("students"), value: overview.students ?? 0, hint: `${t("activeStudents")} ${overview.active ?? 0}` },
    { label: t("submissionRate"), value: `${overview.submitRate ?? 0}%`, hint: t("weeklyTrend") },
    { label: t("accuracy"), value: `${overview.accuracyAvg ?? 0}%`, hint: t("monthlyTrend") },
    { label: t("pending"), value: overview.risk ?? 0, hint: t("validation") }
  ], [overview, t]);

  async function refresh() {
    setStatus("loading");
    try {
      const next = await apiRequest(`/api/class/overview?lang=${encodeURIComponent(locale)}`);
      setData({ ...emptyOverview, ...next });
      setStatus("ready");
    } catch {
      setData(emptyOverview);
      setStatus("failed");
    }
  }

  useEffect(() => {
    refresh();
  }, [locale]);

  return (
    <div className="page-stack">
      <section className="page-heading">
        <div>
          <h1>{t("dashboard")}</h1>
          <p>{t("classOverview")}</p>
        </div>
        <div className="heading-actions">
          <Button icon={RefreshCw} onClick={refresh}>{t("refresh")}</Button>
          <Button icon={Download} variant="primary" onClick={() => window.print()}>{t("exportOverview")}</Button>
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
              <h2>{t("weeklyTrend")}</h2>
              <p>{t("submissionRate")} / {t("accuracy")}</p>
            </div>
          </div>
          <BarSet items={data.weekly || []} />
        </article>

        <article className="panel">
          <div className="panel-head">
            <div>
              <h2>{t("aiAdvice")}</h2>
              <p>{status === "loading" ? t("loading") : t("rewardList")}</p>
            </div>
          </div>
          <div className="list">
            {(advice.length ? advice : [t("noData")]).slice(0, 5).map((line, index) => (
              <div className="list-row" key={`${line}-${index}`}>
                <span className="row-index">{index + 1}</span>
                <span>{line}</span>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="content-grid two">
        <article className="panel">
          <div className="panel-head">
            <div>
              <h2>{t("classOverview")}</h2>
              <p>{classes.length} {t("classManagement")}</p>
            </div>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>{t("classManagement")}</th>
                  <th>{t("students")}</th>
                  <th>{t("submissionRate")}</th>
                  <th>{t("accuracy")}</th>
                  <th>{t("pending")}</th>
                </tr>
              </thead>
              <tbody>
                {classes.length ? classes.map((item) => (
                  <tr key={item.id || item.name}>
                    <td>{item.name}</td>
                    <td>{item.total ?? 0}</td>
                    <td>{rate(item.submitted, item.total)}%</td>
                    <td>{item.accuracy ?? 0}%</td>
                    <td>
                      <StatusPill tone={Number(item.risk || 0) > 3 ? "danger" : Number(item.risk || 0) > 0 ? "warn" : "success"}>
                        {item.risk ?? 0}
                      </StatusPill>
                    </td>
                  </tr>
                )) : (
                  <tr><td colSpan="5">{t("noData")}</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </article>

        <article className="panel">
          <div className="panel-head">
            <div>
              <h2>{t("rewardList")}</h2>
              <p>{t("accuracy")} / {t("submissionRate")}</p>
            </div>
          </div>
          <div className="list">
            {(praises.length ? praises : []).slice(0, 6).map((item) => (
              <div className="list-row split" key={`${item.name}-${item.className}`}>
                <div>
                  <strong>{item.name}</strong>
                  <small>{item.className}</small>
                </div>
                <StatusPill tone="success">{item.accuracy ?? 0}%</StatusPill>
              </div>
            ))}
            {!praises.length ? <div className="empty-state">{t("noData")}</div> : null}
          </div>
        </article>
      </section>
    </div>
  );
}
