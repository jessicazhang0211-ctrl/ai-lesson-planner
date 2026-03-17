import csv
import json
import os
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import run_experiments as rex

BASE = Path(__file__).resolve().parent
RESULTS_DIR = BASE / "results"


def load_json(name: str):
    with (BASE / name).open("r", encoding="utf-8") as f:
        return json.load(f)


def choose_tasks(all_tasks):
    # Default to full dissertation set (36 tasks). Can be overridden by env var.
    # EXPERIMENT_RETEST_TASKS=3 keeps quick smoke mode.
    try:
        max_tasks = int(os.getenv("EXPERIMENT_RETEST_TASKS", "36"))
    except Exception:
        max_tasks = 36
    max_tasks = max(1, max_tasks)

    if max_tasks >= len(all_tasks):
        return all_tasks
    return all_tasks[:max_tasks]


def extract_model_text(provider: str, raw_body: str) -> str:
    if not raw_body:
        return ""
    try:
        obj = json.loads(raw_body)
    except Exception:
        return raw_body.strip()[:8000]

    p = provider.lower()
    if p == "google":
        cands = obj.get("candidates", [])
        if cands:
            parts = cands[0].get("content", {}).get("parts", [])
            return "\n".join(p.get("text", "") for p in parts if isinstance(p, dict)).strip()
        return json.dumps(obj, ensure_ascii=False)

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
            txt = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    txt.append(item.get("text", ""))
            return "\n".join(txt).strip()

    return json.dumps(obj, ensure_ascii=False)


def parse_json_like(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    if t.startswith("```"):
        t = t.strip("`")
        # best effort remove markdown fence header
        if "\n" in t:
            t = t.split("\n", 1)[1]
    if not (t.startswith("{") and t.endswith("}")):
        return False
    try:
        json.loads(t)
        return True
    except Exception:
        return False


def judge_output(judge_model: str, prompt: str, timeout_s: int):
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
    t = (txt or "").strip()
    if t.startswith("```"):
        t = t.strip("`")
        if "\n" in t:
            t = t.split("\n", 1)[1]

    obj = None
    try:
        obj = json.loads(t)
    except Exception:
        # best effort: extract first JSON object block
        s = t.find("{")
        e = t.rfind("}")
        if s != -1 and e != -1 and e > s:
            frag = t[s : e + 1]
            try:
                obj = json.loads(frag)
            except Exception:
                obj = None
        if obj is None:
            return None, "judge_parse_error"

    return obj, "ok"


def build_judge_prompt(task_obj: dict, condition: str, output_text: str):
    rubric = {
        "scale": "1-5 integer",
        "dimensions": [
            "curriculum_alignment",
            "pedagogical_quality",
            "age_appropriateness",
            "misconception_handling",
            "differentiation_quality",
            "json_and_format_reliability",
            "safety_and_policy_compliance",
        ],
        "notes": [
            "teacher-facing only",
            "UK primary maths context",
            "be strict and evidence-based",
            "return JSON only",
        ],
    }

    return (
        "You are an expert UK primary maths lesson-plan evaluator. "
        "Score the candidate output on 7 dimensions using 1-5 integer scale. "
        "If evidence is missing, give lower score.\n\n"
        "Return JSON EXACTLY with fields:\n"
        "{\n"
        '  "curriculum_alignment": int,\n'
        '  "pedagogical_quality": int,\n'
        '  "age_appropriateness": int,\n'
        '  "misconception_handling": int,\n'
        '  "differentiation_quality": int,\n'
        '  "json_and_format_reliability": int,\n'
        '  "safety_and_policy_compliance": int,\n'
        '  "brief_reason": "<=40 words"\n'
        "}\n\n"
        "[TASK]\n"
        + json.dumps(task_obj, ensure_ascii=False)
        + "\n\n[CONDITION]\n"
        + condition
        + "\n\n[RUBRIC]\n"
        + json.dumps(rubric, ensure_ascii=False)
        + "\n\n[CANDIDATE_OUTPUT]\n"
        + (output_text or "")[:12000]
    )


def clamp_int_1_5(v):
    try:
        x = int(round(float(v)))
    except Exception:
        return 1
    return max(1, min(5, x))


def main():
    rex.load_env_file(BASE / ".env")

    tasks = load_json("uk_primary_math_task_set_36.json")["tasks"]
    matrix = load_json("uk_primary_math_model_test_matrix.json")
    req_tpl = load_json("uk_primary_math_generation_request_example.json")
    guardrails = load_json("uk_primary_math_model_guardrails.json")

    tasks = choose_tasks(tasks)
    conditions = [
        "direct_prompting",
        "curriculum_grounded_rag",
        "rag_plus_age_aware_guardrails",
    ]

    allowlist = rex.parse_allowlist(os.getenv("EXPERIMENT_MODEL_ALLOWLIST", ""))
    core = matrix.get("recommended_main_dissertation_setup", {}).get("models", [])

    model_items = []
    for m in matrix.get("core_experiment_set", []):
        if m.get("model") in core:
            if allowlist and m.get("model") not in allowlist:
                continue
            model_items.append(m)

    timeout_s = int(os.getenv("EXPERIMENT_TIMEOUT_SECONDS", "45"))
    judge_model = os.getenv("EVAL_JUDGE_MODEL", "gpt-5-mini")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    detail_csv = RESULTS_DIR / f"retest_scoring_details_{stamp}.csv"
    rank_csv = RESULTS_DIR / f"retest_scoring_ranking_{stamp}.csv"
    rank_md = RESULTS_DIR / f"retest_scoring_ranking_{stamp}.md"

    rows = []
    print(f"Re-test tasks={len(tasks)}, models={len(model_items)}, conditions={len(conditions)}, judge={judge_model}")

    for m in model_items:
        provider = m.get("provider", "")
        model = m.get("model", "")
        api_key = rex.pick_provider_key(provider)

        if not api_key:
            print(f"Skip no key: {provider}/{model}")
            continue

        for condition in conditions:
            for task in tasks:
                req_obj = dict(req_tpl)
                req_obj["year_group"] = task["year_group"]
                req_obj["key_stage"] = task["key_stage"]
                req_obj["topic"] = task["topic"]
                req_obj["duration_minutes"] = task["duration_minutes"]
                req_obj["class_profile"]["attainment_profile"] = task.get("class_profile", "mixed attainment")
                req_obj["class_profile"]["prior_learning"] = task.get("prior_learning", [])
                req_obj["class_profile"]["send_notes"] = task.get("support_needs", [])

                prompt = rex.compose_prompt(condition, req_obj, guardrails)
                t0 = time.time()
                code, body = rex.run_once(provider, model, prompt, timeout_s)
                latency_ms = round((time.time() - t0) * 1000, 2)

                output_text = extract_model_text(provider, body)
                json_like = parse_json_like(output_text)
                status = "OK" if 200 <= code < 300 else "HTTP_ERROR"

                # default scores when generation failed
                scores = {
                    "curriculum_alignment": 1,
                    "pedagogical_quality": 1,
                    "age_appropriateness": 1,
                    "misconception_handling": 1,
                    "differentiation_quality": 1,
                    "json_and_format_reliability": 1,
                    "safety_and_policy_compliance": 1,
                    "brief_reason": "generation failed",
                }
                judge_status = "skipped"

                if status == "OK":
                    jprompt = build_judge_prompt(task, condition, output_text)
                    judged, judge_status = judge_output(judge_model, jprompt, timeout_s)
                    if judged:
                        for k in [
                            "curriculum_alignment",
                            "pedagogical_quality",
                            "age_appropriateness",
                            "misconception_handling",
                            "differentiation_quality",
                            "json_and_format_reliability",
                            "safety_and_policy_compliance",
                        ]:
                            scores[k] = clamp_int_1_5(judged.get(k, 1))
                        scores["brief_reason"] = str(judged.get("brief_reason", ""))[:160]
                    else:
                        # Judge parsing failure should not be treated as model failure.
                        # Use neutral scores to avoid unfairly biasing the ranking.
                        scores = {
                            "curriculum_alignment": 3,
                            "pedagogical_quality": 3,
                            "age_appropriateness": 3,
                            "misconception_handling": 3,
                            "differentiation_quality": 3,
                            "json_and_format_reliability": 3,
                            "safety_and_policy_compliance": 3,
                            "brief_reason": "judge parse fallback: neutral=3",
                        }

                rows.append(
                    {
                        "task_id": task.get("task_id"),
                        "provider": provider,
                        "model": model,
                        "condition": condition,
                        "http_code": code,
                        "status": status,
                        "latency_ms": latency_ms,
                        "json_like": json_like,
                        "judge_status": judge_status,
                        **scores,
                    }
                )
                print(f"[{provider}/{model}] {condition} {task.get('task_id')} -> {code}, judge={judge_status}")

    fields = [
        "task_id",
        "provider",
        "model",
        "condition",
        "http_code",
        "status",
        "latency_ms",
        "json_like",
        "judge_status",
        "curriculum_alignment",
        "pedagogical_quality",
        "age_appropriateness",
        "misconception_handling",
        "differentiation_quality",
        "json_and_format_reliability",
        "safety_and_policy_compliance",
        "brief_reason",
    ]

    with detail_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    # aggregate ranking
    agg = defaultdict(lambda: {
        "n": 0,
        "ok": 0,
        "json_like": 0,
        "latency_sum": 0.0,
        "c1": 0.0,
        "c2": 0.0,
        "c3": 0.0,
        "c4": 0.0,
        "c5": 0.0,
        "fmt": 0.0,
        "safe": 0.0,
    })

    for r in rows:
        key = (r["provider"], r["model"])
        d = agg[key]
        d["n"] += 1
        d["ok"] += 1 if r["status"] == "OK" else 0
        d["json_like"] += 1 if str(r["json_like"]).lower() in {"true", "1", "yes"} else 0
        d["latency_sum"] += float(r["latency_ms"])
        d["c1"] += float(r["curriculum_alignment"])
        d["c2"] += float(r["pedagogical_quality"])
        d["c3"] += float(r["age_appropriateness"])
        d["c4"] += float(r["misconception_handling"])
        d["c5"] += float(r["differentiation_quality"])
        d["fmt"] += float(r["json_and_format_reliability"])
        d["safe"] += float(r["safety_and_policy_compliance"])

    min_latency = min((d["latency_sum"] / d["n"]) for d in agg.values()) if agg else 1.0

    rank_rows = []
    for (provider, model), d in agg.items():
        n = d["n"]
        ok_rate = d["ok"] * 100.0 / n if n else 0.0
        json_rate = d["json_like"] * 100.0 / n if n else 0.0
        avg_latency = d["latency_sum"] / n if n else 0.0
        edu_mean_5 = (d["c1"] + d["c2"] + d["c3"] + d["c4"] + d["c5"]) / (5.0 * n) if n else 1.0
        fmt_mean = d["fmt"] / n if n else 1.0
        safe_mean = d["safe"] / n if n else 1.0

        # gate per requested order
        gate_pass = (ok_rate >= 90.0) and (json_rate >= 90.0) and (safe_mean >= 3.5)

        # scoring: education first, then objective reliability, then efficiency
        teaching_quality_score = edu_mean_5 * 20.0
        objective_reliability = (ok_rate + json_rate) / 2.0
        efficiency_score = (min_latency / avg_latency) * 100.0 if avg_latency else 0.0
        final_score = 0.6 * teaching_quality_score + 0.25 * objective_reliability + 0.15 * efficiency_score

        rank_rows.append(
            {
                "provider": provider,
                "model": model,
                "runs": n,
                "ok_rate_percent": round(ok_rate, 2),
                "json_like_rate_percent": round(json_rate, 2),
                "avg_latency_ms": round(avg_latency, 2),
                "curriculum_alignment": round(d["c1"] / n, 2),
                "pedagogical_quality": round(d["c2"] / n, 2),
                "age_appropriateness": round(d["c3"] / n, 2),
                "misconception_handling": round(d["c4"] / n, 2),
                "differentiation_quality": round(d["c5"] / n, 2),
                "json_and_format_reliability": round(fmt_mean, 2),
                "safety_and_policy_compliance": round(safe_mean, 2),
                "edu_mean_5": round(edu_mean_5, 2),
                "gate_pass": gate_pass,
                "teaching_quality_score": round(teaching_quality_score, 2),
                "objective_reliability_score": round(objective_reliability, 2),
                "efficiency_score": round(efficiency_score, 2),
                "final_score": round(final_score, 2),
            }
        )

    rank_rows.sort(key=lambda x: (not x["gate_pass"], -x["edu_mean_5"], -x["final_score"], x["avg_latency_ms"]))
    for i, r in enumerate(rank_rows, start=1):
        r["rank"] = i

    rank_fields = [
        "rank",
        "provider",
        "model",
        "runs",
        "gate_pass",
        "edu_mean_5",
        "curriculum_alignment",
        "pedagogical_quality",
        "age_appropriateness",
        "misconception_handling",
        "differentiation_quality",
        "json_and_format_reliability",
        "safety_and_policy_compliance",
        "ok_rate_percent",
        "json_like_rate_percent",
        "avg_latency_ms",
        "teaching_quality_score",
        "objective_reliability_score",
        "efficiency_score",
        "final_score",
    ]

    with rank_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rank_fields)
        w.writeheader()
        w.writerows(rank_rows)

    lines = []
    lines.append("# 按标准重测评分排名")
    lines.append("")
    lines.append(f"- Details: {detail_csv.name}")
    lines.append(f"- Ranking CSV: {rank_csv.name}")
    lines.append("- Gate: OK>=90%, JSON-like>=90%, Safety>=3.5")
    lines.append("- Priority: 教学质量(前5维均分) > 客观可靠性 > 效率")
    lines.append("- Final Score = 0.6*Teaching + 0.25*Reliability + 0.15*Efficiency")
    lines.append("")
    lines.append("| Rank | Provider | Model | Gate | EduMean(1-5) | C1 | C2 | C3 | C4 | C5 | Safety | OK% | Latency(ms) | Final |")
    lines.append("|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in rank_rows:
        lines.append(
            f"| {r['rank']} | {r['provider']} | {r['model']} | {r['gate_pass']} | {r['edu_mean_5']:.2f} | {r['curriculum_alignment']:.2f} | {r['pedagogical_quality']:.2f} | {r['age_appropriateness']:.2f} | {r['misconception_handling']:.2f} | {r['differentiation_quality']:.2f} | {r['safety_and_policy_compliance']:.2f} | {r['ok_rate_percent']:.2f} | {r['avg_latency_ms']:.2f} | {r['final_score']:.2f} |"
        )

    rank_md.write_text("\n".join(lines), encoding="utf-8")

    print("Done")
    print(f"Details: {detail_csv}")
    print(f"Ranking CSV: {rank_csv}")
    print(f"Ranking MD: {rank_md}")


if __name__ == "__main__":
    main()
