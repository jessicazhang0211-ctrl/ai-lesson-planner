import csv
import json
import os
from datetime import datetime
from pathlib import Path

import run_experiments as rex

BASE = Path(__file__).resolve().parent
OUT_BASE = BASE / "JIAOANTEST"


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


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


def parse_openai_body(raw_body: str):
    if not raw_body:
        return None
    try:
        return json.loads(raw_body)
    except Exception:
        return None


def extract_openai_core_fields(obj: dict):
    if not obj:
        return {
            "content": "",
            "finish_reason": "",
            "completion_tokens": 0,
            "reasoning_tokens": 0,
        }

    content = ""
    finish_reason = ""
    completion_tokens = 0
    reasoning_tokens = 0

    choices = obj.get("choices", [])
    if choices:
        c0 = choices[0]
        finish_reason = c0.get("finish_reason", "") or ""
        msg = c0.get("message", {})
        raw_content = msg.get("content", "")
        if isinstance(raw_content, str):
            content = raw_content
        elif isinstance(raw_content, list):
            texts = []
            for item in raw_content:
                if isinstance(item, dict) and item.get("type") == "text":
                    texts.append(item.get("text", ""))
            content = "\n".join(texts)

    usage = obj.get("usage", {})
    completion_tokens = int(usage.get("completion_tokens", 0) or 0)
    completion_detail = usage.get("completion_tokens_details", {})
    reasoning_tokens = int(completion_detail.get("reasoning_tokens", 0) or 0)

    return {
        "content": content,
        "finish_reason": finish_reason,
        "completion_tokens": completion_tokens,
        "reasoning_tokens": reasoning_tokens,
    }


def main():
    rex.load_env_file(BASE / ".env")

    # Make empty-content behavior easier to reproduce in GPT-5 family.
    os.environ["EXPERIMENT_MAX_OUTPUT_TOKENS"] = os.getenv("EXPERIMENT_MAX_OUTPUT_TOKENS", "512")

    tasks = load_json(BASE / "uk_primary_math_task_set_36.json").get("tasks", [])
    template_obj = load_json(BASE / "example.json")

    target_count = int(os.getenv("OPENAI_EMPTY_CASE_TARGET", "15"))
    model = os.getenv("OPENAI_REVIEW_MODEL", "gpt-5.4")
    timeout_s = int(os.getenv("EXPERIMENT_TIMEOUT_SECONDS", "90"))
    max_attempts = int(os.getenv("OPENAI_EMPTY_CASE_MAX_ATTEMPTS", "120"))

    if not os.getenv("OPENAI_API_KEY", ""):
        raise RuntimeError("OPENAI_API_KEY is missing")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = OUT_BASE / f"openai_empty_manual_review_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    index_rows = []
    collected = 0
    attempts = 0

    # Cycle tasks until collected enough empty-content cases or attempts limit reached.
    while collected < target_count and attempts < max_attempts:
        task = tasks[attempts % len(tasks)]
        attempts += 1

        prompt = build_generation_prompt(task, template_obj)
        code, body = rex.run_once("OpenAI", model, prompt, timeout_s)

        obj = parse_openai_body(body)
        core = extract_openai_core_fields(obj)
        content = core["content"] or ""
        is_empty_content = content.strip() == ""

        if code == 200 and is_empty_content:
            collected += 1
            case_id = f"case_{collected:02d}"

            case_payload = {
                "case_id": case_id,
                "task": {
                    "task_id": task.get("task_id"),
                    "year_group": task.get("year_group"),
                    "key_stage": task.get("key_stage"),
                    "topic": task.get("topic"),
                    "duration_minutes": task.get("duration_minutes"),
                },
                "request": {
                    "provider": "OpenAI",
                    "model": model,
                    "timeout_seconds": timeout_s,
                    "max_output_tokens_env": os.environ.get("EXPERIMENT_MAX_OUTPUT_TOKENS", ""),
                    "prompt_preview": prompt[:1800],
                },
                "response_summary": {
                    "http_code": code,
                    "finish_reason": core["finish_reason"],
                    "completion_tokens": core["completion_tokens"],
                    "reasoning_tokens": core["reasoning_tokens"],
                    "is_empty_content": True,
                },
                "raw_response": obj if obj is not None else (body or ""),
            }

            case_path = out_dir / f"{case_id}.json"
            case_path.write_text(json.dumps(case_payload, ensure_ascii=False, indent=2), encoding="utf-8")

            index_rows.append(
                {
                    "case_id": case_id,
                    "task_id": task.get("task_id"),
                    "year_group": task.get("year_group"),
                    "topic": task.get("topic"),
                    "http_code": code,
                    "finish_reason": core["finish_reason"],
                    "completion_tokens": core["completion_tokens"],
                    "reasoning_tokens": core["reasoning_tokens"],
                    "case_file": case_path.name,
                }
            )
            print(f"Collected {case_id}: {task.get('task_id')} finish={core['finish_reason']}")

    index_path = out_dir / "index.csv"
    with index_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "case_id",
                "task_id",
                "year_group",
                "topic",
                "http_code",
                "finish_reason",
                "completion_tokens",
                "reasoning_tokens",
                "case_file",
            ],
        )
        w.writeheader()
        w.writerows(index_rows)

    summary = {
        "target_count": target_count,
        "collected_count": collected,
        "attempts": attempts,
        "model": model,
        "timeout_seconds": timeout_s,
        "max_output_tokens_env": os.environ.get("EXPERIMENT_MAX_OUTPUT_TOKENS", ""),
        "index_file": str(index_path),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Done")
    print(f"Output Dir: {out_dir}")
    print(f"Collected: {collected}/{target_count}")
    print(f"Index: {index_path}")


if __name__ == "__main__":
    main()
