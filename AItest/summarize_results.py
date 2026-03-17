import csv
import os
from collections import defaultdict, Counter
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
RESULTS_DIR = BASE / "results"


def to_bool(v):
    return str(v).strip().lower() in {"1", "true", "yes"}


def latest_csv(run_tag: str = ""):
    if run_tag:
        files = sorted(RESULTS_DIR.glob(f"experiment_runs_{run_tag}_*.csv"))
    else:
        files = sorted(RESULTS_DIR.glob("experiment_runs_*.csv"))
    if not files:
        if run_tag:
            raise FileNotFoundError(f"No experiment_runs_{run_tag}_*.csv found in AItest/results")
        raise FileNotFoundError("No experiment_runs_*.csv found in AItest/results")
    return files[-1]


def load_rows(path: Path):
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def safe_float(x):
    try:
        return float(x)
    except Exception:
        return 0.0


def aggregate(rows):
    group = defaultdict(lambda: {"n": 0, "ok": 0, "json_like": 0, "latency_sum": 0.0, "http": Counter()})
    by_model = defaultdict(lambda: {"n": 0, "ok": 0, "latency_sum": 0.0})
    by_condition = defaultdict(lambda: {"n": 0, "ok": 0, "latency_sum": 0.0})

    total = len(rows)
    ok_total = 0
    json_total = 0

    for r in rows:
        provider = r.get("provider", "")
        model = r.get("model", "")
        condition = r.get("condition", "")
        status = r.get("status", "")
        code = str(r.get("http_code", ""))
        latency = safe_float(r.get("latency_ms"))
        is_ok = status == "OK"
        is_json = to_bool(r.get("json_like", ""))

        key = (provider, model, condition)
        g = group[key]
        g["n"] += 1
        g["ok"] += 1 if is_ok else 0
        g["json_like"] += 1 if is_json else 0
        g["latency_sum"] += latency
        g["http"][code] += 1

        m = by_model[(provider, model)]
        m["n"] += 1
        m["ok"] += 1 if is_ok else 0
        m["latency_sum"] += latency

        c = by_condition[condition]
        c["n"] += 1
        c["ok"] += 1 if is_ok else 0
        c["latency_sum"] += latency

        ok_total += 1 if is_ok else 0
        json_total += 1 if is_json else 0

    return {
        "total": total,
        "ok_total": ok_total,
        "json_total": json_total,
        "group": group,
        "by_model": by_model,
        "by_condition": by_condition,
    }


def pct(a, b):
    if not b:
        return 0.0
    return round(a * 100.0 / b, 2)


def write_summary_files(input_csv: Path, agg, run_tag: str = ""):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if run_tag:
        out_csv = RESULTS_DIR / f"summary_table_{run_tag}_{stamp}.csv"
        out_md = RESULTS_DIR / f"summary_report_{run_tag}_{stamp}.md"
    else:
        out_csv = RESULTS_DIR / f"summary_table_{stamp}.csv"
        out_md = RESULTS_DIR / f"summary_report_{stamp}.md"

    # Flat summary CSV for paper tables
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "provider",
            "model",
            "condition",
            "runs",
            "ok_runs",
            "ok_rate_percent",
            "json_like_rate_percent",
            "avg_latency_ms",
            "top_http_code",
        ])
        for (provider, model, condition), d in sorted(agg["group"].items()):
            n = d["n"]
            ok = d["ok"]
            json_like = d["json_like"]
            avg_latency = round(d["latency_sum"] / n, 2) if n else 0.0
            top_http = d["http"].most_common(1)[0][0] if d["http"] else ""
            w.writerow([
                provider,
                model,
                condition,
                n,
                ok,
                pct(ok, n),
                pct(json_like, n),
                avg_latency,
                top_http,
            ])

    # Markdown report for dissertation
    lines = []
    lines.append("# AItest 实验自动汇总报告")
    lines.append("")
    lines.append(f"- 源文件: {input_csv.name}")
    lines.append(f"- 运行标识: {run_tag or '-'}")
    lines.append(f"- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- 总运行数: {agg['total']}")
    lines.append(f"- HTTP 成功数(2xx): {agg['ok_total']}")
    lines.append(f"- JSON-like 比例: {pct(agg['json_total'], agg['total'])}%")
    lines.append("")

    lines.append("## 表 1 模型总览")
    lines.append("")
    lines.append("| Provider | Model | Runs | OK Rate(%) | Avg Latency(ms) |")
    lines.append("|---|---|---:|---:|---:|")
    for (provider, model), d in sorted(agg["by_model"].items()):
        n = d["n"]
        ok_rate = pct(d["ok"], n)
        avg_latency = round(d["latency_sum"] / n, 2) if n else 0.0
        lines.append(f"| {provider} | {model} | {n} | {ok_rate} | {avg_latency} |")
    lines.append("")

    lines.append("## 表 2 配置组总览")
    lines.append("")
    lines.append("| Condition | Runs | OK Rate(%) | Avg Latency(ms) |")
    lines.append("|---|---:|---:|---:|")
    for condition, d in sorted(agg["by_condition"].items()):
        n = d["n"]
        ok_rate = pct(d["ok"], n)
        avg_latency = round(d["latency_sum"] / n, 2) if n else 0.0
        lines.append(f"| {condition} | {n} | {ok_rate} | {avg_latency} |")
    lines.append("")

    lines.append("## 表 3 模型 x 配置对比")
    lines.append("")
    lines.append("| Provider | Model | Condition | Runs | OK Rate(%) | JSON-like(%) | Avg Latency(ms) | Top HTTP |")
    lines.append("|---|---|---|---:|---:|---:|---:|---:|")
    for (provider, model, condition), d in sorted(agg["group"].items()):
        n = d["n"]
        ok = d["ok"]
        json_like = d["json_like"]
        avg_latency = round(d["latency_sum"] / n, 2) if n else 0.0
        top_http = d["http"].most_common(1)[0][0] if d["http"] else ""
        lines.append(
            f"| {provider} | {model} | {condition} | {n} | {pct(ok,n)} | {pct(json_like,n)} | {avg_latency} | {top_http} |"
        )
    lines.append("")

    if agg["ok_total"] == 0:
        lines.append("## 诊断提示")
        lines.append("")
        lines.append("本批次没有成功响应（OK=0），通常表示 API Key 无效/余额不足/权限未开通。")
        lines.append("建议先用单一模型做 1 条任务冒烟测试，再扩大到 36 任务。")

    out_md.write_text("\n".join(lines), encoding="utf-8")
    return out_csv, out_md


def main():
    run_tag = (os.getenv("EXPERIMENT_RUN_TAG", "") or "").strip().lower()
    src = latest_csv(run_tag=run_tag)
    rows = load_rows(src)
    agg = aggregate(rows)
    out_csv, out_md = write_summary_files(src, agg, run_tag=run_tag)
    print(f"Source: {src}")
    print(f"Summary CSV: {out_csv}")
    print(f"Summary MD: {out_md}")


if __name__ == "__main__":
    main()
