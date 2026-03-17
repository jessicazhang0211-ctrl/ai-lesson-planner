import csv
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
RESULTS_DIR = BASE / "results"


def latest_fixed_summary_table() -> Path:
    files = sorted(RESULTS_DIR.glob("summary_table_report_required_fixed_*.csv"))
    if not files:
        raise FileNotFoundError("No summary_table_report_required_fixed_*.csv found in AItest/results")
    return files[-1]


def safe_float(x: str) -> float:
    try:
        return float(x)
    except Exception:
        return 0.0


def load_rows(path: Path):
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def build_model_summary(rows):
    # Aggregate across conditions for each model
    data = {}
    for r in rows:
        key = (r["provider"], r["model"])
        data.setdefault(
            key,
            {
                "provider": r["provider"],
                "model": r["model"],
                "runs": 0.0,
                "ok_runs": 0.0,
                "latency_sum": 0.0,
                "groups": 0.0,
            },
        )
        d = data[key]
        d["runs"] += safe_float(r.get("runs", "0"))
        d["ok_runs"] += safe_float(r.get("ok_runs", "0"))
        d["latency_sum"] += safe_float(r.get("avg_latency_ms", "0"))
        d["groups"] += 1.0

    models = []
    for _, d in data.items():
        avg_latency = d["latency_sum"] / d["groups"] if d["groups"] else 0.0
        ok_rate = (d["ok_runs"] * 100.0 / d["runs"]) if d["runs"] else 0.0
        d["avg_latency_ms"] = avg_latency
        d["ok_rate_percent"] = ok_rate
        models.append(d)
    return models


def score_models(models):
    # Objective-only ranking using current run outputs:
    # final_score = 0.7 * reliability_score + 0.3 * latency_score
    # reliability_score = OK rate (0-100)
    # latency_score = min_latency / model_latency * 100
    # (higher is better)
    min_latency = min(m["avg_latency_ms"] for m in models) if models else 1.0

    for m in models:
        reliability_score = m["ok_rate_percent"]
        latency_score = (min_latency / m["avg_latency_ms"]) * 100.0 if m["avg_latency_ms"] else 0.0
        final_score = 0.7 * reliability_score + 0.3 * latency_score

        m["reliability_score"] = reliability_score
        m["latency_score"] = latency_score
        m["final_score"] = final_score

    models.sort(key=lambda x: (-x["final_score"], x["avg_latency_ms"], x["model"]))

    for i, m in enumerate(models, start=1):
        m["rank"] = i

    return models


def write_outputs(src: Path, ranked):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_csv = RESULTS_DIR / f"model_ranking_report_required_fixed_{stamp}.csv"
    out_md = RESULTS_DIR / f"model_ranking_report_required_fixed_{stamp}.md"

    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "rank",
                "provider",
                "model",
                "runs",
                "ok_rate_percent",
                "avg_latency_ms",
                "reliability_score",
                "latency_score",
                "final_score",
            ]
        )
        for m in ranked:
            w.writerow(
                [
                    m["rank"],
                    m["provider"],
                    m["model"],
                    int(m["runs"]),
                    round(m["ok_rate_percent"], 2),
                    round(m["avg_latency_ms"], 2),
                    round(m["reliability_score"], 2),
                    round(m["latency_score"], 2),
                    round(m["final_score"], 2),
                ]
            )

    lines = []
    lines.append("# 模型排名（report_required_fixed）")
    lines.append("")
    lines.append(f"- Source: {src.name}")
    lines.append("- Scoring: final_score = 0.7 * reliability_score + 0.3 * latency_score")
    lines.append("- reliability_score = OK rate (0-100)")
    lines.append("- latency_score = min_latency / model_latency * 100")
    lines.append("")
    lines.append("| Rank | Provider | Model | Runs | OK Rate(%) | Avg Latency(ms) | Reliability | Latency Score | Final Score |")
    lines.append("|---:|---|---|---:|---:|---:|---:|---:|---:|")
    for m in ranked:
        lines.append(
            "| {rank} | {provider} | {model} | {runs} | {ok:.2f} | {lat:.2f} | {rel:.2f} | {ls:.2f} | {fs:.2f} |".format(
                rank=m["rank"],
                provider=m["provider"],
                model=m["model"],
                runs=int(m["runs"]),
                ok=m["ok_rate_percent"],
                lat=m["avg_latency_ms"],
                rel=m["reliability_score"],
                ls=m["latency_score"],
                fs=m["final_score"],
            )
        )

    out_md.write_text("\n".join(lines), encoding="utf-8")
    return out_csv, out_md


def main():
    src = latest_fixed_summary_table()
    rows = load_rows(src)
    model_summary = build_model_summary(rows)
    ranked = score_models(model_summary)
    out_csv, out_md = write_outputs(src, ranked)

    print(f"Source: {src}")
    print(f"Ranking CSV: {out_csv}")
    print(f"Ranking MD: {out_md}")


if __name__ == "__main__":
    main()
