import csv
import json
import os
import time
import http.client
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
RESULTS_DIR = BASE / "results"


def load_json(name: str):
    with (BASE / name).open("r", encoding="utf-8") as f:
        return json.load(f)


def get_max_output_tokens() -> int:
    try:
        v = int(os.getenv("EXPERIMENT_MAX_OUTPUT_TOKENS", "1024"))
    except Exception:
        v = 1024
    return max(64, v)


def get_openai_max_completion_tokens() -> int:
    try:
        v = int(os.getenv("EXPERIMENT_OPENAI_MAX_COMPLETION_TOKENS", "8192"))
    except Exception:
        v = 8192
    return max(64, v)


def get_effective_output_tokens(provider: str, model: str, token_param_name: str) -> int:
    p = (provider or "").lower()
    m = (model or "").strip().lower()

    # Model-level override from env, e.g.:
    # EXPERIMENT_MODEL_MAX_OUTPUT_TOKENS="openai:gpt-5=8192,google:gemini-2.5-pro=4096"
    override_raw = (os.getenv("EXPERIMENT_MODEL_MAX_OUTPUT_TOKENS", "") or "").strip()
    if override_raw:
        for item in override_raw.split(","):
            pair = item.strip()
            if not pair or "=" not in pair or ":" not in pair:
                continue
            left, right = pair.split("=", 1)
            pp, mm = left.split(":", 1)
            if p == pp.strip().lower() and m == mm.strip().lower():
                try:
                    return max(64, int(right.strip()))
                except Exception:
                    pass

    # Raised defaults for models that previously returned empty content in JIAOAN tests.
    raised_defaults = {
        ("openai", "gpt-5"): get_openai_max_completion_tokens(),
        ("openai", "gpt-5-mini"): get_openai_max_completion_tokens(),
        ("google", "gemini-2.5-pro"): 4096,
        ("deepseek", "deepseek-reasoner"): 4096,
    }

    if (p, m) in raised_defaults:
        return raised_defaults[(p, m)]

    if token_param_name == "max_completion_tokens":
        return get_openai_max_completion_tokens()
    return get_max_output_tokens()


def load_env_file(path: Path):
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        key = k.strip()
        # 允许命令行临时覆盖实验规模参数
        if key in {"EXPERIMENT_MAX_TASKS", "EXPERIMENT_TIMEOUT_SECONDS", "EXPERIMENT_MODEL_ALLOWLIST", "EXPERIMENT_RUN_TAG"} and key in os.environ:
            continue
        # .env 应覆盖终端里旧值，避免沿用过期 key
        os.environ[key] = v.strip()


def post_json(url: str, headers: dict, payload: dict, timeout_s: int):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        max_retries = int(os.getenv("EXPERIMENT_REQUEST_RETRIES", "2"))
    except Exception:
        max_retries = 2
    max_retries = max(0, max_retries)

    last_err = ""
    for attempt in range(max_retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                body = resp.read().decode("utf-8", errors="ignore")
                return resp.getcode(), body
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            return e.code, body
        except Exception as e:
            last_err = f"REQUEST_EXCEPTION: {type(e).__name__}: {str(e)}"
            if attempt >= max_retries:
                break
            time.sleep(min(6, 1.5 * (attempt + 1)))

    return 0, last_err


def normalize_model_name(provider: str, model: str) -> str:
    """Map report-friendly model labels to provider API model IDs."""
    p = (provider or "").lower()
    m = (model or "").strip()

    if p == "anthropic":
        amap = {
            "Claude Opus 4.6": "claude-opus-4-6",
            "Claude Sonnet 4.6": "claude-sonnet-4-6",
            "Claude Haiku 4.5": "claude-3-5-haiku-latest",
        }
        return amap.get(m, m)

    if p == "google":
        gmap = {
            "Gemini 2.5 Pro": "gemini-2.5-pro",
            "Gemini 2.5 Flash": "gemini-2.5-flash",
            "Gemini 2.5 Flash-Lite": "gemini-2.5-flash-lite",
            "Gemini 3.1 Pro Preview": "gemini-2.5-pro",
        }
        return gmap.get(m, m)

    if p == "openai":
        omap = {
            "gpt-5.4": "gpt-5",
            "gpt-5-mini": "gpt-5-mini",
        }
        return omap.get(m, m)

    if p == "deepseek":
        dmap = {
            "deepseek-reasoner": "deepseek-reasoner",
            "deepseek-chat": "deepseek-chat",
        }
        return dmap.get(m, m)

    if "qwen" in p or "alibaba" in p:
        qmap = {
            "qwen3.5-plus": "qwen-plus",
            "qwen3.5-flash": "qwen-turbo",
        }
        return qmap.get(m, m)

    return m


def compose_prompt(condition: str, request_obj: dict, guardrails: dict):
    return (
        "You are running in UK primary maths dissertation experiment mode. "
        f"Condition={condition}. "
        "Follow guardrails and return JSON only.\n\n"
        "[REQUEST]\n"
        + json.dumps(request_obj, ensure_ascii=False)
        + "\n\n[GUARDRAILS]\n"
        + json.dumps(guardrails, ensure_ascii=False)
    )


def call_openai_like(base_url: str, api_key: str, model: str, prompt: str, timeout_s: int, temperature=None, token_param_name: str = "max_tokens", max_output_tokens: int | None = None):
    url = base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Return valid JSON only."},
            {"role": "user", "content": prompt},
        ],
    }
    payload[token_param_name] = max(64, int(max_output_tokens)) if max_output_tokens is not None else get_max_output_tokens()
    if temperature is not None:
        payload["temperature"] = temperature
    code, body = post_json(url, headers, payload, timeout_s)
    return code, body


def call_anthropic(base_url: str, api_key: str, model: str, prompt: str, timeout_s: int, max_output_tokens: int | None = None):
    url = base_url.rstrip("/") + "/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": max(64, int(max_output_tokens)) if max_output_tokens is not None else get_max_output_tokens(),
        "temperature": 0.2,
        "messages": [{"role": "user", "content": prompt}],
    }
    code, body = post_json(url, headers, payload, timeout_s)
    return code, body


def call_gemini(api_key: str, model: str, prompt: str, timeout_s: int, max_output_tokens: int | None = None):
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        + model
        + ":generateContent?key="
        + api_key
    )
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": max(64, int(max_output_tokens)) if max_output_tokens is not None else get_max_output_tokens(),
        },
    }
    code, body = post_json(url, headers, payload, timeout_s)
    return code, body


def pick_provider_key(provider: str):
    p = provider.lower()
    if p == "openai":
        return os.getenv("OPENAI_API_KEY", "")
    if p == "anthropic":
        return os.getenv("ANTHROPIC_API_KEY", "")
    if p == "google":
        return os.getenv("GEMINI_API_KEY", "")
    if p == "deepseek":
        return os.getenv("DEEPSEEK_API_KEY", "")
    if "qwen" in p or "alibaba" in p:
        return os.getenv("QWEN_API_KEY", "")
    return ""


def run_once(provider: str, model: str, prompt: str, timeout_s: int):
    p = provider.lower()
    api_model = normalize_model_name(provider, model)
    if p == "openai":
        # GPT-5 系列在 chat/completions 下通常仅支持默认 temperature
        budget = get_effective_output_tokens(provider, api_model, "max_completion_tokens")
        return call_openai_like(
            os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            os.getenv("OPENAI_API_KEY", ""),
            api_model,
            prompt,
            timeout_s,
            temperature=None,
            token_param_name="max_completion_tokens",
            max_output_tokens=budget,
        )
    if p == "anthropic":
        budget = get_effective_output_tokens(provider, api_model, "max_tokens")
        return call_anthropic(
            os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1"),
            os.getenv("ANTHROPIC_API_KEY", ""),
            api_model,
            prompt,
            timeout_s,
            max_output_tokens=budget,
        )
    if p == "google":
        budget = get_effective_output_tokens(provider, api_model, "maxOutputTokens")
        return call_gemini(os.getenv("GEMINI_API_KEY", ""), api_model, prompt, timeout_s, max_output_tokens=budget)
    if p == "deepseek":
        budget = get_effective_output_tokens(provider, api_model, "max_tokens")
        return call_openai_like(
            os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
            os.getenv("DEEPSEEK_API_KEY", ""),
            api_model,
            prompt,
            timeout_s,
            temperature=0.2,
            max_output_tokens=budget,
        )
    if "qwen" in p or "alibaba" in p:
        budget = get_effective_output_tokens(provider, api_model, "max_tokens")
        return call_openai_like(
            os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
            os.getenv("QWEN_API_KEY", ""),
            api_model,
            prompt,
            timeout_s,
            temperature=0.2,
            max_output_tokens=budget,
        )
    return 0, "UNSUPPORTED_PROVIDER"


def try_extract_json_text(raw_body: str):
    txt = (raw_body or "").strip()
    if not txt:
        return False
    if txt.startswith("{") and txt.endswith("}"):
        try:
            json.loads(txt)
            return True
        except Exception:
            return False
    return False


def parse_allowlist(raw: str):
    if not raw:
        return set()
    return {x.strip() for x in raw.split(",") if x.strip()}


def main():
    load_env_file(BASE / ".env")

    tasks = load_json("uk_primary_math_task_set_36.json")["tasks"]
    matrix = load_json("uk_primary_math_model_test_matrix.json")
    req_tpl = load_json("uk_primary_math_generation_request_example.json")
    guardrails = load_json("uk_primary_math_model_guardrails.json")

    conditions = [
        "direct_prompting",
        "curriculum_grounded_rag",
        "rag_plus_age_aware_guardrails",
    ]

    max_tasks = int(os.getenv("EXPERIMENT_MAX_TASKS", "36"))
    timeout_s = int(os.getenv("EXPERIMENT_TIMEOUT_SECONDS", "90"))
    allowlist = parse_allowlist(os.getenv("EXPERIMENT_MODEL_ALLOWLIST", ""))
    run_tag = (os.getenv("EXPERIMENT_RUN_TAG", "") or "").strip().lower()
    tasks = tasks[:max_tasks]

    core = matrix.get("core_experiment_set") or []
    if allowlist:
        core = [m for m in core if (m.get("model") or "") in allowlist]

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if run_tag:
        csv_path = RESULTS_DIR / f"experiment_runs_{run_tag}_{stamp}.csv"
    else:
        csv_path = RESULTS_DIR / f"experiment_runs_{stamp}.csv"

    rows = []
    print(f"Running tag={run_tag or '-'}, tasks={len(tasks)}, models={len(core)}, timeout={timeout_s}s")
    for model_item in core:
        provider = model_item.get("provider", "")
        model_name = model_item.get("model", "")
        api_key = pick_provider_key(provider)

        if not api_key:
            rows.append({
                "task_id": "-",
                "provider": provider,
                "model": model_name,
                "condition": "-",
                "status": "SKIPPED_NO_KEY",
                "latency_ms": 0,
                "http_code": 0,
                "json_like": False,
                "note": "missing api key",
            })
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

                prompt = compose_prompt(condition, req_obj, guardrails)

                t0 = time.time()
                code, body = run_once(provider, model_name, prompt, timeout_s)
                latency_ms = round((time.time() - t0) * 1000, 2)

                rows.append({
                    "task_id": task.get("task_id"),
                    "provider": provider,
                    "model": model_name,
                    "condition": condition,
                    "status": "OK" if 200 <= code < 300 else "HTTP_ERROR",
                    "latency_ms": latency_ms,
                    "http_code": code,
                    "json_like": try_extract_json_text(body),
                    "note": (body[:160].replace("\n", " ") if code >= 400 or code == 0 else ""),
                })
                print(f"[{provider}/{model_name}] {condition} {task.get('task_id')} -> {code} in {latency_ms}ms")

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["task_id", "provider", "model", "condition", "status", "latency_ms", "http_code", "json_like", "note"],
        )
        writer.writeheader()
        writer.writerows(rows)

    print("Done.")
    print(f"CSV: {csv_path}")


if __name__ == "__main__":
    main()
