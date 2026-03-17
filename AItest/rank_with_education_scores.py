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


def latest_human_eval_file() -> Path:
    files = sorted(RESULTS_DIR.glob("human_eval_scores_*.csv"))
    if not files:
        raise FileNotFoundError(
            "No human_eval_scores_*.csv found. Please copy template file and fill scores first."
        )
    return files[-1]


def safe_float(x: str) -> float:
    try:
        return float(x)
    except Exception:
        return 0.0


def read_csv(path: Path):
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def aggregate_objective(rows):
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

    out = {}
    for key, d in data.items():
        out[key] = {
            "provider": d["provider"],
            "model": d["model"],
            "runs": d["runs"],
            "ok_rate_percent": (d["ok_runs"] * 100.0 / d["runs"]) if d["runs"] else 0.0,
            "avg_latency_ms": (d["latency_sum"] / d["groups"]) if d["groups"] else 0.0,
        }
    return out


def parse_score_1_5(v: str, field_name: str, model_name: str) -> float:
    x = safe_float(v)
    if x < 1 or x > 5:
        raise ValueError(f"{model_name} field {field_name} must be in [1,5], got {v}")
    return x


def load_education_scores(rows):
    out = {}
    for r in rows:
        key = (r["provider"], r["model"])
        model_name = f"{r['provider']}/{r['model']}"

        c1 = parse_score_1_5(r.get("curriculum_alignment", ""), "curriculum_alignment", model_name)
        c2 = parse_score_1_5(r.get("pedagogical_quality", ""), "pedagogical_quality", model_name)
        c3 = parse_score_1_5(r.get("age_appropriateness", ""), "age_appropriateness", model_name)
        c4 = parse_score_1_5(r.get("misconception_handling", ""), "misconception_handling", model_name)
        c5 = parse_score_1_5(r.get("differentiation_quality", ""), "differentiation_quality", model_name)

        edu_mean_5 = (c1 + c2 + c3 + c4 + c5) / 5.0
        edu_score_100 = edu_mean_5 * 20.0

        out[key] = {
            "c1": c1,
            "c2": c2,
            "c3": c3,
            "c4": c4,
            "c5": c5,
            "edu_mean_5": edu_mean_5,
            "edu_score_100": edu_score_100,
            "n_raters": r.get("n_raters", ""),
            "n_samples": r.get("n_samples", ""),
            "notes": r.get("notes", ""),
        }
    return out


def rank_models(obj, edu):
    keys = sorted(set(obj.keys()) & set(edu.keys()))
    if not keys:
        raise ValueError("No overlapping models between summary table and human evaluation file")

    min_latency = min(obj[k]["avg_latency_ms"] for k in keys)

    rows = []
    for k in keys:
        o = obj[k]
        e = edu[k]

        reliability_score = o["ok_rate_percent"]
        latency_score = (min_latency / o["avg_latency_ms"]) * 100.0 if o["avg_latency_ms"] else 0.0
        teaching_quality_score = e["edu_score_100"]

        # 教学质量优先：60% 教学质量 + 25% 可靠性 + 15% 时延
        final_score = 0.6 * teaching_quality_score + 0.25 * reliability_score + 0.15 * latency_score

        rows.append(
            {
                "provider": o["provider"],
                "model": o["model"],
                "runs": o["runs"],
                "ok_rate_percent": o["ok_rate_percent"],
                "avg_latency_ms": o["avg_latency_ms"],
                "curriculum_alignment": e["c1"],
                "pedagogical_quality": e["c2"],
                "age_appropriateness": e["c3"],
                "misconception_handling": e["c4"],
                "differentiation_quality": e["c5"],
                "edu_mean_5": e["edu_mean_5"],
                "teaching_quality_score": teaching_quality_score,
                "reliability_score": reliability_score,
                "latency_score": latency_score,
                "final_score": final_score,
                "n_raters": e["n_raters"],
                "n_samples": e["n_samples"],
                "notes": e["notes"],
            }
        )

    rows.sort(key=lambda x: (-x["final_score"], -x["edu_mean_5"], x["avg_latency_ms"]))
    for i, r in enumerate(rows, start=1):
        r["rank"] = i
    return rows


def write_outputs(src_summary: Path, src_edu: Path, rows):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_csv = RESULTS_DIR / f"model_ranking_with_education_{stamp}.csv"
    out_md = RESULTS_DIR / f"model_ranking_with_education_{stamp}.md"

    fields = [
        "rank",
        "provider",
        "model",
        "runs",
        "ok_rate_percent",
        "avg_latency_ms",
        "curriculum_alignment",
        "pedagogical_quality",
        "age_appropriateness",
        "misconception_handling",
        "differentiation_quality",
        "edu_mean_5",
        "teaching_quality_score",
        "reliability_score",
        "latency_score",
        "final_score",
        "n_raters",
        "n_samples",
        "notes",
    ]

    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            out = dict(r)
            for k in [
                "ok_rate_percent",
                "avg_latency_ms",
                "curriculum_alignment",
                "pedagogical_quality",
                "age_appropriateness",
                "misconception_handling",
                "differentiation_quality",
                "edu_mean_5",
                "teaching_quality_score",
                "reliability_score",
                "latency_score",
                "final_score",
            ]:
                out[k] = round(float(out[k]), 2)
            out["runs"] = int(float(out["runs"]))
            w.writerow(out)

    lines = []
    lines.append("# 模型排名（教学质量优先）")
    lines.append("")
    lines.append(f"- Objective Source: {src_summary.name}")
    lines.append(f"- Human Eval Source: {src_edu.name}")
    lines.append("- Final Score = 0.6 * TeachingQuality + 0.25 * Reliability + 0.15 * Latency")
    lines.append("- TeachingQuality = 前5教育维度均分 * 20")
    lines.append("")
    lines.append("| Rank | Provider | Model | Edu Mean(1-5) | Teaching(0-100) | OK Rate(%) | Avg Latency(ms) | Final Score |")
    lines.append("|---:|---|---|---:|---:|---:|---:|---:|")
    for r in rows:
        lines.append(
            f"| {r['rank']} | {r['provider']} | {r['model']} | {r['edu_mean_5']:.2f} | {r['teaching_quality_score']:.2f} | {r['ok_rate_percent']:.2f} | {r['avg_latency_ms']:.2f} | {r['final_score']:.2f} |"
        )

    out_md.write_text("\n".join(lines), encoding="utf-8")
    return out_csv, out_md


def main():
    src_summary = latest_fixed_summary_table()
    src_edu = latest_human_eval_file()

    obj_rows = read_csv(src_summary)
    edu_rows = read_csv(src_edu)

    obj = aggregate_objective(obj_rows)
    edu = load_education_scores(edu_rows)
    ranked = rank_models(obj, edu)

    out_csv, out_md = write_outputs(src_summary, src_edu, ranked)
    print(f"Objective Source: {src_summary}")
    print(f"Human Eval Source: {src_edu}")
    print(f"Ranking CSV: {out_csv}")
    print(f"Ranking MD: {out_md}")


if __name__ == "__main__":
    main()
