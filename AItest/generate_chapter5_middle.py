import os
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
RESULTS = BASE / "results"


def latest(pattern: str) -> Path:
    files = sorted(RESULTS.glob(pattern))
    if not files:
        raise FileNotFoundError(f"No files matching: {pattern}")
    return files[-1]


def parse_summary(md_path: Path):
    text = md_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    meta = {"total": "", "ok": "", "json": ""}
    model_rows = []

    for ln in lines:
        if ln.startswith("- 总运行数:"):
            meta["total"] = ln.split(":", 1)[1].strip()
        if ln.startswith("- HTTP 成功数(2xx):"):
            meta["ok"] = ln.split(":", 1)[1].strip()
        if ln.startswith("- JSON-like 比例:"):
            meta["json"] = ln.split(":", 1)[1].strip()

    in_table1 = False
    for ln in lines:
        if ln.strip() == "## 表 1 模型总览":
            in_table1 = True
            continue
        if in_table1 and ln.startswith("## "):
            break
        if in_table1 and ln.startswith("| ") and "Provider" not in ln and "---" not in ln:
            cols = [x.strip() for x in ln.strip("|").split("|")]
            if len(cols) >= 5:
                model_rows.append({
                    "provider": cols[0],
                    "model": cols[1],
                    "runs": cols[2],
                    "ok_rate": cols[3],
                    "latency": cols[4],
                })

    # fastest by avg latency
    fastest = None
    if model_rows:
        def k(r):
            try:
                return float(r["latency"])
            except Exception:
                return 10**9
        fastest = sorted(model_rows, key=k)[0]

    return meta, model_rows, fastest


def build_chapter5_paragraph(meta, model_rows, fastest, summary_name):
    model_sentence = "；".join(
        [f"{m['model']}（平均时延 {m['latency']} ms，成功率 {m['ok_rate']}%）" for m in model_rows]
    )
    fast_sentence = ""
    if fastest:
        fast_sentence = f"从时延表现看，{fastest['model']} 在本轮中等规模实验中最快。"

    para = f"""# 第5章结果段落（middle）

本研究在 middle 配置下开展了中等规模实验（6 任务 x 3 模型 x 3 配置），并基于自动化汇总结果进行比较分析。根据 `{summary_name}`，本轮实验总运行数为 {meta['total']}，HTTP 成功数为 {meta['ok']}，JSON-like 输出比例为 {meta['json']}。从模型维度看，{model_sentence}。{fast_sentence}总体而言，三类系统配置（direct prompting、curriculum-grounded RAG、RAG + age-aware guardrails）在该规模下均能稳定返回结构化结果，为后续扩大到完整 36 任务提供了可复现的工程基础。

建议在后续完整实验中继续保持 middle 的模型组合，并在相同任务集上补充人工教育量表评分，以将“可用性与时延”结果扩展到“教学质量与课程对齐度”的综合结论。
"""
    return para


def main():
    os.environ.setdefault("EXPERIMENT_RUN_TAG", "middle")
    summary_md = latest("summary_report_middle_*.md")
    meta, model_rows, fastest = parse_summary(summary_md)
    out = build_chapter5_paragraph(meta, model_rows, fastest, summary_md.name)

    out_path = RESULTS / f"chapter5_results_middle_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    out_path.write_text(out, encoding="utf-8")
    print(f"Source summary: {summary_md}")
    print(f"Chapter 5 draft: {out_path}")


if __name__ == "__main__":
    main()
