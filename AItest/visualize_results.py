import csv
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt

BASE = Path(__file__).resolve().parent
RESULTS_DIR = BASE / "results"


def latest_fixed_summary_table() -> Path:
    files = sorted(RESULTS_DIR.glob("summary_table_report_required_fixed_*.csv"))
    if not files:
        raise FileNotFoundError("No summary_table_report_required_fixed_*.csv found in AItest/results")
    return files[-1]


def read_rows(csv_path: Path):
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def to_float(v: str) -> float:
    try:
        return float(v)
    except Exception:
        return 0.0


def aggregate_by_model(rows):
    data = {}
    for r in rows:
        model = r["model"]
        data.setdefault(model, {"ok_rates": [], "latencies": []})
        data[model]["ok_rates"].append(to_float(r["ok_rate_percent"]))
        data[model]["latencies"].append(to_float(r["avg_latency_ms"]))

    models = sorted(data.keys())
    ok_rates = [sum(data[m]["ok_rates"]) / len(data[m]["ok_rates"]) for m in models]
    latencies = [sum(data[m]["latencies"]) / len(data[m]["latencies"]) for m in models]
    return models, ok_rates, latencies


def aggregate_by_condition(rows):
    data = {}
    for r in rows:
        cond = r["condition"]
        data.setdefault(cond, {"ok_rates": [], "latencies": []})
        data[cond]["ok_rates"].append(to_float(r["ok_rate_percent"]))
        data[cond]["latencies"].append(to_float(r["avg_latency_ms"]))

    conditions = sorted(data.keys())
    ok_rates = [sum(data[c]["ok_rates"]) / len(data[c]["ok_rates"]) for c in conditions]
    latencies = [sum(data[c]["latencies"]) / len(data[c]["latencies"]) for c in conditions]
    return conditions, ok_rates, latencies


def build_latency_matrix(rows):
    models = sorted({r["model"] for r in rows})
    conditions = sorted({r["condition"] for r in rows})
    value = {(r["model"], r["condition"]): to_float(r["avg_latency_ms"]) for r in rows}

    matrix = []
    for m in models:
        row = []
        for c in conditions:
            row.append(value.get((m, c), 0.0))
        matrix.append(row)
    return models, conditions, matrix


def save_bar(labels, values, title, ylabel, out_path, color="#2b8a3e"):
    fig, ax = plt.subplots(figsize=(12, 6))
    bars = ax.bar(labels, values, color=color)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.25)
    ax.tick_params(axis="x", labelrotation=25)

    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{val:.2f}", ha="center", va="bottom", fontsize=8)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def save_heatmap(models, conditions, matrix, out_path):
    fig, ax = plt.subplots(figsize=(11, 6))
    im = ax.imshow(matrix, cmap="YlGnBu", aspect="auto")

    ax.set_title("Avg Latency Heatmap (ms)")
    ax.set_xticks(range(len(conditions)))
    ax.set_xticklabels(conditions, rotation=20)
    ax.set_yticks(range(len(models)))
    ax.set_yticklabels(models)

    for i in range(len(models)):
        for j in range(len(conditions)):
            ax.text(j, i, f"{matrix[i][j]:.0f}", ha="center", va="center", color="black", fontsize=8)

    fig.colorbar(im, ax=ax, label="ms")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def write_index_md(stamp: str, source_csv: Path, files):
    md = RESULTS_DIR / f"visualization_report_{stamp}.md"
    lines = [
        "# AItest Results Visualization",
        "",
        f"- Source CSV: {source_csv.name}",
        f"- Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Charts",
    ]
    for f in files:
        lines.append(f"- {f.name}")
    lines.append("")
    for f in files:
        lines.append(f"### {f.name}")
        lines.append(f"![]({f.name})")
        lines.append("")

    md.write_text("\n".join(lines), encoding="utf-8")
    return md


def main():
    src = latest_fixed_summary_table()
    rows = read_rows(src)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    models, model_ok_rates, model_latencies = aggregate_by_model(rows)
    conditions, condition_ok_rates, condition_latencies = aggregate_by_condition(rows)
    hm_models, hm_conditions, matrix = build_latency_matrix(rows)

    out1 = RESULTS_DIR / f"viz_model_avg_latency_{stamp}.png"
    out2 = RESULTS_DIR / f"viz_condition_avg_latency_{stamp}.png"
    out3 = RESULTS_DIR / f"viz_model_ok_rate_{stamp}.png"
    out4 = RESULTS_DIR / f"viz_condition_ok_rate_{stamp}.png"
    out5 = RESULTS_DIR / f"viz_latency_heatmap_{stamp}.png"

    save_bar(models, model_latencies, "Average Latency by Model", "Latency (ms)", out1, color="#1f77b4")
    save_bar(conditions, condition_latencies, "Average Latency by Condition", "Latency (ms)", out2, color="#ff7f0e")
    save_bar(models, model_ok_rates, "OK Rate by Model", "OK Rate (%)", out3, color="#2ca02c")
    save_bar(conditions, condition_ok_rates, "OK Rate by Condition", "OK Rate (%)", out4, color="#d62728")
    save_heatmap(hm_models, hm_conditions, matrix, out5)

    report = write_index_md(stamp, src, [out1, out2, out3, out4, out5])

    print(f"Source: {src}")
    print(f"Report: {report}")
    print("Charts:")
    for p in [out1, out2, out3, out4, out5]:
        print(p)


if __name__ == "__main__":
    main()
