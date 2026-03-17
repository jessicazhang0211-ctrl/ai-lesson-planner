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


def main():
    src = latest_fixed_summary_table()

    models = {}
    with src.open("r", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            key = (r["provider"], r["model"])
            models[key] = {
                "provider": r["provider"],
                "model": r["model"],
            }

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = RESULTS_DIR / f"human_eval_scores_template_{stamp}.csv"

    fields = [
        "provider",
        "model",
        "curriculum_alignment",
        "pedagogical_quality",
        "age_appropriateness",
        "misconception_handling",
        "differentiation_quality",
        "n_raters",
        "n_samples",
        "notes",
    ]

    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for _, row in sorted(models.items(), key=lambda x: (x[0][0], x[0][1])):
            w.writerow(
                {
                    "provider": row["provider"],
                    "model": row["model"],
                    "curriculum_alignment": "",
                    "pedagogical_quality": "",
                    "age_appropriateness": "",
                    "misconception_handling": "",
                    "differentiation_quality": "",
                    "n_raters": "",
                    "n_samples": "",
                    "notes": "score 1-5",
                }
            )

    print(f"Source: {src}")
    print(f"Template: {out}")


if __name__ == "__main__":
    main()
