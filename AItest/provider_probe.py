import json
import os
import urllib.error
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent


def load_env_file(path: Path):
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()


def post(url: str, headers: dict, payload: dict, timeout: int = 40):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8", errors="ignore")
            return r.getcode(), body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        return e.code, body
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}"


def main():
    load_env_file(BASE / ".env")
    prompt = "Reply with JSON only."

    checks = []

    checks.append((
        "openai_chat_gpt5mini",
        os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/") + "/chat/completions",
        {
            "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY', '')}",
            "Content-Type": "application/json",
        },
        {
            "model": "gpt-5-mini",
            "messages": [
                {"role": "system", "content": "Return valid JSON only."},
                {"role": "user", "content": prompt},
            ],
        },
    ))

    checks.append((
        "anthropic_sonnet46",
        os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1").rstrip("/") + "/messages",
        {
            "x-api-key": os.getenv("ANTHROPIC_API_KEY", ""),
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        {
            "model": "claude-sonnet-4-6",
            "max_tokens": 256,
            "messages": [{"role": "user", "content": prompt}],
        },
    ))

    checks.append((
        "deepseek_chat",
        os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1").rstrip("/") + "/chat/completions",
        {
            "Authorization": f"Bearer {os.getenv('DEEPSEEK_API_KEY', '')}",
            "Content-Type": "application/json",
        },
        {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
        },
    ))

    checks.append((
        "qwen_turbo",
        os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1").rstrip("/") + "/chat/completions",
        {
            "Authorization": f"Bearer {os.getenv('QWEN_API_KEY', '')}",
            "Content-Type": "application/json",
        },
        {
            "model": "qwen-turbo",
            "messages": [{"role": "user", "content": prompt}],
        },
    ))

    checks.append((
        "gemini_flash",
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key="
        + os.getenv("GEMINI_API_KEY", ""),
        {"Content-Type": "application/json"},
        {"contents": [{"parts": [{"text": prompt}]}]},
    ))

    for name, url, headers, payload in checks:
        code, body = post(url, headers, payload)
        snippet = (body or "").replace("\n", " ")[:220]
        print(f"{name}: status={code}; body={snippet}")


if __name__ == "__main__":
    main()
