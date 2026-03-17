import csv
import hashlib
import json
import os
import time
from datetime import datetime
from pathlib import Path

import run_experiments as rex
import run_jiaoan_36_test as jiaoan


BASE = Path(__file__).resolve().parent
OUT_DIR = BASE / "JIAOANTEST"


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def find_latest_details_csv() -> Path:
    files = sorted(OUT_DIR.glob("jiaoan_test_details_*.csv"), key=lambda p: p.stat().st_mtime)
    if not files:
        raise FileNotFoundError("No jiaoan_test_details_*.csv found in JIAOANTEST")
    return files[-1]


def snapshot_text(text: str, limit: int = 3000) -> str:
    t = (text or "").strip()
    if len(t) <= limit:
        return t
    return t[:limit] + "\n...[TRUNCATED]..."


def main():
    rex.load_env_file(BASE / ".env")

    details_csv = find_latest_details_csv()
    task_set = load_json(BASE / "uk_primary_math_task_set_36.json")
    template_obj = load_json(BASE / "example.json")

    timeout_s = int(os.getenv("EXPERIMENT_TIMEOUT_SECONDS", "90"))
    capture_n = int(os.getenv("OPENAI_SNAPSHOT_COUNT", "15"))

    task_by_id = {t.get("task_id"): t for t in task_set.get("tasks", [])}

    selected = []
    with details_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("provider") == "OpenAI":
                selected.append(row)
            if len(selected) >= capture_n:
                break

    if not selected:
        raise RuntimeError("No OpenAI rows found in details CSV")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_csv = OUT_DIR / f"openai_first{len(selected)}_raw_snapshots_{stamp}.csv"
    out_md = OUT_DIR / f"openai_first{len(selected)}_raw_snapshots_{stamp}.md"

    rows = []
    md_lines = ["# OpenAI 前15份原始模型返回文本快照", ""]
    md_lines.append(f"- Source details: {details_csv.name}")
    md_lines.append(f"- Captured rows: {len(selected)}")
    md_lines.append("")

    for i, item in enumerate(selected, start=1):
        task_id = item.get("task_id", "")
        provider = item.get("provider", "")
        model = item.get("model", "")

        task = task_by_id.get(task_id)
        if not task:
            continue

        prompt = jiaoan.build_generation_prompt(task, template_obj)
        t0 = time.time()
        code, body = rex.run_once(provider, model, prompt, timeout_s)
        latency_ms = round((time.time() - t0) * 1000, 2)

        extracted = jiaoan.extract_model_text(provider, body)
        row = {
            "seq": i,
            "task_id": task_id,
            "provider": provider,
            "model": model,
            "http_code": code,
            "latency_ms": latency_ms,
            "raw_body_len": len(body or ""),
            "extracted_text_len": len(extracted or ""),
            "raw_body_sha256_16": hashlib.sha256((body or "").encode("utf-8", errors="ignore")).hexdigest()[:16],
            "raw_body_snapshot": snapshot_text(body, 3000),
            "extracted_text_snapshot": snapshot_text(extracted, 3000),
        }
        rows.append(row)

        md_lines.append(f"## {i}. {task_id} | {model} | HTTP {code}")
        md_lines.append("")
        md_lines.append("### Raw Body Snapshot")
        md_lines.append("```")
        md_lines.append(row["raw_body_snapshot"])
        md_lines.append("```")
        md_lines.append("")
        md_lines.append("### Extracted Text Snapshot")
        md_lines.append("```")
        md_lines.append(row["extracted_text_snapshot"])
        md_lines.append("```")
        md_lines.append("")

        print(f"[{i}/{len(selected)}] {task_id} {model} -> {code}, raw={row['raw_body_len']}, text={row['extracted_text_len']}")

    fields = [
        "seq",
        "task_id",
        "provider",
        "model",
        "http_code",
        "latency_ms",
        "raw_body_len",
        "extracted_text_len",
        "raw_body_sha256_16",
        "raw_body_snapshot",
        "extracted_text_snapshot",
    ]
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    out_md.write_text("\n".join(md_lines), encoding="utf-8")

    print("Done")
    print(f"OUT_CSV={out_csv}")
    print(f"OUT_MD={out_md}")


if __name__ == "__main__":
    main()
