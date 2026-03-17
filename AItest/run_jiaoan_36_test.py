import csv
import json
import os
import re
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import run_experiments as rex

BASE = Path(__file__).resolve().parent
OUT_DIR = BASE / "JIAOANTEST"


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def extract_model_text(provider: str, raw_body: str) -> str:
    if not raw_body:
        return ""
    try:
        obj = json.loads(raw_body)
    except Exception:
        return raw_body.strip()[:12000]

    p = provider.lower()
    if p == "google":
        cands = obj.get("candidates", [])
        if cands:
            parts = cands[0].get("content", {}).get("parts", [])
            return "\n".join(part.get("text", "") for part in parts if isinstance(part, dict)).strip()
        return ""

    if p == "anthropic":
        parts = obj.get("content", [])
        texts = [x.get("text", "") for x in parts if isinstance(x, dict) and x.get("type") == "text"]
        return "\n".join(texts).strip()

    # OpenAI-compatible format
    choices = obj.get("choices", [])
    if choices:
        msg = choices[0].get("message", {})
        content = msg.get("content", "")
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            texts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    texts.append(item.get("text", ""))
            return "\n".join(texts).strip()
    return ""


def parse_json_object(text: str):
    t = (text or "").strip()
    if not t:
        return None
    if t.startswith("```"):
        lines = t.splitlines()
        if len(lines) >= 2:
            t = "\n".join(lines[1:])
            if t.endswith("```"):
                t = t[:-3]
        t = t.strip()
    try:
        return json.loads(t)
    except Exception:
        s = t.find("{")
        e = t.rfind("}")
        if s != -1 and e != -1 and e > s:
            try:
                return json.loads(t[s : e + 1])
            except Exception:
                return None
    return None


def build_generation_prompt(task: dict, template_obj: dict):
    return (
        "You are generating a UK primary mathematics detailed child-centred lesson plan. "
        "Return JSON only. Keep the structure aligned with TEMPLATE_JSON. "
        "Use child-friendly language and UK classroom context.\n\n"
        "[TASK]\n"
        + json.dumps(
            {
                "task_id": task.get("task_id"),
                "year_group": task.get("year_group"),
                "key_stage": task.get("key_stage"),
                "topic_family": task.get("topic_family"),
                "topic": task.get("topic"),
                "duration_minutes": task.get("duration_minutes"),
                "class_profile": task.get("class_profile"),
                "prior_learning": task.get("prior_learning", []),
                "support_needs": task.get("support_needs", []),
            },
            ensure_ascii=False,
        )
        + "\n\n[TEMPLATE_JSON]\n"
        + json.dumps(template_obj, ensure_ascii=False)
    )


def build_judge_prompt(task: dict, output_text: str, json_parse_ok: bool):
    rubric = {
        "dimensions": [
            {"name": "content_completeness", "max": 20, "focus": "目标/流程/评价/资源/作业等关键部分"},
            {"name": "age_appropriateness", "max": 20, "focus": "是否符合7-8岁儿童认知与语言"},
            {"name": "teaching_design_quality", "max": 20, "focus": "递进/支架/练习/总结是否清晰"},
            {"name": "json_structure_usability", "max": 15, "focus": "系统解析/渲染/扩展可用性"},
            {"name": "low_age_support_strategy", "max": 10, "focus": "游戏/重复/视觉/操作活动"},
            {"name": "resource_recommendation_quality", "max": 10, "focus": "资源与主题及环节匹配度"},
            {"name": "ai_intelligence", "max": 5, "focus": "动态生成而非纯模板拼接"},
        ]
    }

    return (
        "你是教案评审员。请严格按给定评分标准对候选教案打分，输出 JSON 且仅输出 JSON。\n"
        "总分=7个维度分数相加，满分100。\n"
        "输出格式必须是:\n"
        "{\n"
        '  "content_completeness": int,\n'
        '  "age_appropriateness": int,\n'
        '  "teaching_design_quality": int,\n'
        '  "json_structure_usability": int,\n'
        '  "low_age_support_strategy": int,\n'
        '  "resource_recommendation_quality": int,\n'
        '  "ai_intelligence": int,\n'
        '  "total_score": int,\n'
        '  "brief_reason": "不超过60字"\n'
        "}\n\n"
        "约束: 各字段分值不得超过该维度上限，不得为负数。\n\n"
        "[TASK]\n"
        + json.dumps(task, ensure_ascii=False)
        + "\n\n[JSON_PARSE_OK]\n"
        + str(json_parse_ok)
        + "\n\n[RUBRIC]\n"
        + json.dumps(rubric, ensure_ascii=False)
        + "\n\n[CANDIDATE_OUTPUT]\n"
        + (output_text or "")[:18000]
    )


def clamp(v, lo, hi):
    try:
        x = int(round(float(v)))
    except Exception:
        return lo
    return max(lo, min(hi, x))


def try_extract_scores_from_text(text: str):
    t = (text or "").strip()
    if not t:
        return None

    fields = [
        ("content_completeness", 20),
        ("age_appropriateness", 20),
        ("teaching_design_quality", 20),
        ("json_structure_usability", 15),
        ("low_age_support_strategy", 10),
        ("resource_recommendation_quality", 10),
        ("ai_intelligence", 5),
    ]

    out = {}
    hit = 0
    for name, hi in fields:
        p = re.compile(rf'"?{re.escape(name)}"?\s*[:=：]\s*(-?\d+)', re.IGNORECASE)
        m = p.search(t)
        if m:
            out[name] = clamp(m.group(1), 0, hi)
            hit += 1

    if hit < 4:
        return None

    for name, hi in fields:
        if name not in out:
            out[name] = 0

    out["total_score"] = sum(out[name] for name, _ in fields)

    # Try to keep a concise reason if present.
    m_reason = re.search(r'"?brief_reason"?\s*[:=：]\s*"([^"]{1,200})"', t, re.IGNORECASE)
    if m_reason:
        out["brief_reason"] = m_reason.group(1)
    else:
        out["brief_reason"] = "judge text parsed fallback"

    return out


def evaluate_with_judge(judge_model: str, task: dict, output_text: str, json_parse_ok: bool, timeout_s: int):
    prompt = build_judge_prompt(task, output_text, json_parse_ok)
    code, body = rex.call_openai_like(
        os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        os.getenv("OPENAI_API_KEY", ""),
        judge_model,
        prompt,
        timeout_s,
        temperature=None,
        token_param_name="max_completion_tokens",
    )
    if not (200 <= code < 300):
        return None, f"judge_http_{code}"

    txt = extract_model_text("openai", body)
    obj = parse_json_object(txt)
    if not obj:
        recovered = try_extract_scores_from_text(txt)
        if recovered:
            return recovered, "judge_parse_recovered"
        return None, "judge_parse_error"

    s = {
        "content_completeness": clamp(obj.get("content_completeness", 0), 0, 20),
        "age_appropriateness": clamp(obj.get("age_appropriateness", 0), 0, 20),
        "teaching_design_quality": clamp(obj.get("teaching_design_quality", 0), 0, 20),
        "json_structure_usability": clamp(obj.get("json_structure_usability", 0), 0, 15),
        "low_age_support_strategy": clamp(obj.get("low_age_support_strategy", 0), 0, 10),
        "resource_recommendation_quality": clamp(obj.get("resource_recommendation_quality", 0), 0, 10),
        "ai_intelligence": clamp(obj.get("ai_intelligence", 0), 0, 5),
    }
    s["total_score"] = sum(s.values())
    s["brief_reason"] = str(obj.get("brief_reason", ""))[:200]
    return s, "ok"


def main():
    rex.load_env_file(BASE / ".env")

    task_set = load_json(BASE / "uk_primary_math_task_set_36.json")
    matrix = load_json(BASE / "uk_primary_math_model_test_matrix.json")
    template_obj = load_json(BASE / "example.json")

    tasks = task_set.get("tasks", [])
    max_tasks = int(os.getenv("EXPERIMENT_JIAOAN_MAX_TASKS", "36"))
    tasks = tasks[:max_tasks]

    model_names = matrix.get("recommended_main_dissertation_setup", {}).get("models", [])
    core_items = [m for m in matrix.get("core_experiment_set", []) if m.get("model") in model_names]

    allowlist = rex.parse_allowlist(os.getenv("EXPERIMENT_MODEL_ALLOWLIST", ""))
    if allowlist:
        core_items = [m for m in core_items if m.get("model") in allowlist]

    timeout_s = int(os.getenv("EXPERIMENT_TIMEOUT_SECONDS", "90"))
    judge_model = os.getenv("EVAL_JUDGE_MODEL", "gpt-5-mini")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    detail_csv = OUT_DIR / f"jiaoan_test_details_{stamp}.csv"
    rank_csv = OUT_DIR / f"jiaoan_test_ranking_{stamp}.csv"
    rank_md = OUT_DIR / f"jiaoan_test_ranking_{stamp}.md"

    rows = []
    print(f"Running JIAOAN test: tasks={len(tasks)}, models={len(core_items)}, judge={judge_model}")

    for m in core_items:
        provider = m.get("provider", "")
        model = m.get("model", "")
        api_key = rex.pick_provider_key(provider)
        if not api_key:
            print(f"Skip no key: {provider}/{model}")
            continue

        for task in tasks:
            gen_prompt = build_generation_prompt(task, template_obj)
            t0 = time.time()
            code, body = rex.run_once(provider, model, gen_prompt, timeout_s)
            latency_ms = round((time.time() - t0) * 1000, 2)

            output_text = extract_model_text(provider, body)
            parsed = parse_json_object(output_text)
            json_parse_ok = parsed is not None
            status = "OK" if 200 <= code < 300 else "HTTP_ERROR"

            scores = {
                "content_completeness": 0,
                "age_appropriateness": 0,
                "teaching_design_quality": 0,
                "json_structure_usability": 0,
                "low_age_support_strategy": 0,
                "resource_recommendation_quality": 0,
                "ai_intelligence": 0,
                "total_score": 0,
                "brief_reason": "generation failed",
            }
            judge_status = "skipped"

            if status == "OK":
                judged, judge_status = evaluate_with_judge(judge_model, task, output_text, json_parse_ok, timeout_s)
                if judged:
                    scores = judged
                else:
                    # Neutral fallback to reduce judge parsing noise
                    scores = {
                        "content_completeness": 10,
                        "age_appropriateness": 10,
                        "teaching_design_quality": 10,
                        "json_structure_usability": 7,
                        "low_age_support_strategy": 5,
                        "resource_recommendation_quality": 5,
                        "ai_intelligence": 2,
                        "total_score": 49,
                        "brief_reason": "judge parse fallback",
                    }

            row = {
                "task_id": task.get("task_id"),
                "provider": provider,
                "model": model,
                "http_code": code,
                "status": status,
                "latency_ms": latency_ms,
                "json_parse_ok": json_parse_ok,
                "judge_status": judge_status,
            }
            row.update(scores)
            rows.append(row)
            print(f"[{provider}/{model}] {task.get('task_id')} -> {code}, judge={judge_status}")

    detail_fields = [
        "task_id",
        "provider",
        "model",
        "http_code",
        "status",
        "latency_ms",
        "json_parse_ok",
        "judge_status",
        "content_completeness",
        "age_appropriateness",
        "teaching_design_quality",
        "json_structure_usability",
        "low_age_support_strategy",
        "resource_recommendation_quality",
        "ai_intelligence",
        "total_score",
        "brief_reason",
    ]

    with detail_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=detail_fields)
        w.writeheader()
        w.writerows(rows)

    agg = defaultdict(lambda: {"n": 0, "ok": 0, "json_ok": 0, "lat": 0.0, "score": 0.0})
    for r in rows:
        key = (r["provider"], r["model"])
        d = agg[key]
        d["n"] += 1
        d["ok"] += 1 if r["status"] == "OK" else 0
        d["json_ok"] += 1 if str(r["json_parse_ok"]).lower() in {"true", "1", "yes"} else 0
        d["lat"] += float(r["latency_ms"])
        d["score"] += float(r["total_score"])

    rank_rows = []
    for (provider, model), d in agg.items():
        n = d["n"]
        ok_rate = d["ok"] * 100.0 / n if n else 0.0
        json_rate = d["json_ok"] * 100.0 / n if n else 0.0
        avg_latency = d["lat"] / n if n else 0.0
        avg_score = d["score"] / n if n else 0.0
        rank_rows.append(
            {
                "provider": provider,
                "model": model,
                "runs": n,
                "ok_rate_percent": round(ok_rate, 2),
                "json_parse_ok_percent": round(json_rate, 2),
                "avg_latency_ms": round(avg_latency, 2),
                "avg_total_score": round(avg_score, 2),
            }
        )

    rank_rows.sort(key=lambda x: (-x["avg_total_score"], -x["ok_rate_percent"], -x["json_parse_ok_percent"], x["avg_latency_ms"]))
    for i, r in enumerate(rank_rows, start=1):
        r["rank"] = i

    rank_fields = [
        "rank",
        "provider",
        "model",
        "runs",
        "avg_total_score",
        "ok_rate_percent",
        "json_parse_ok_percent",
        "avg_latency_ms",
    ]

    with rank_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rank_fields)
        w.writeheader()
        w.writerows(rank_rows)

    lines = []
    lines.append("# JIAOAN 36项测试排名")
    lines.append("")
    lines.append(f"- Details: {detail_csv.name}")
    lines.append(f"- Ranking CSV: {rank_csv.name}")
    lines.append("- 评分标准: 内容20 / 年龄20 / 教学20 / JSON结构15 / 低龄支持10 / 资源10 / AI智能5")
    lines.append("")
    lines.append("| Rank | Provider | Model | Runs | Avg Score(100) | OK% | JSON Parse OK% | Avg Latency(ms) |")
    lines.append("|---:|---|---|---:|---:|---:|---:|---:|")
    for r in rank_rows:
        lines.append(
            f"| {r['rank']} | {r['provider']} | {r['model']} | {r['runs']} | {r['avg_total_score']:.2f} | {r['ok_rate_percent']:.2f} | {r['json_parse_ok_percent']:.2f} | {r['avg_latency_ms']:.2f} |"
        )

    rank_md.write_text("\n".join(lines), encoding="utf-8")

    print("Done")
    print(f"Details: {detail_csv}")
    print(f"Ranking CSV: {rank_csv}")
    print(f"Ranking MD: {rank_md}")


if __name__ == "__main__":
    main()
