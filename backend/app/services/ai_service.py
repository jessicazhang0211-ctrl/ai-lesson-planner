from app.config import Config
import json
import urllib.error
import urllib.request

try:
    import google.generativeai as genai
except Exception:
    genai = None


class AIService:
    def __init__(self):
        self._configured = False

    def _ensure_configured(self):
        if self._configured:
            return
        if not genai or not Config.GEMINI_API_KEY:
            return
        genai.configure(api_key=Config.GEMINI_API_KEY)
        self._configured = True

    def _call_openai_chat(self, prompt: str, model_name: str, max_completion_tokens: int) -> str:
        if not Config.OPENAI_API_KEY:
            raise RuntimeError("OpenAI API key not configured")

        url = Config.OPENAI_BASE_URL.rstrip("/") + "/chat/completions"
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": "Return only the requested lesson-plan content."},
                {"role": "user", "content": prompt},
            ],
            "max_completion_tokens": max(64, int(max_completion_tokens)),
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {Config.OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = resp.read().decode("utf-8", errors="ignore")
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="ignore")
            if e.code == 401:
                raise RuntimeError("OpenAI authentication failed (invalid API key). Please check OPENAI_API_KEY.")
            raise RuntimeError(f"OpenAI HTTP {e.code}: {detail}")
        except Exception as e:
            raise RuntimeError(f"OpenAI request failed: {type(e).__name__}: {str(e)}")

        try:
            obj = json.loads(body)
        except Exception:
            raise RuntimeError("OpenAI returned non-JSON response")

        choices = obj.get("choices", [])
        if not choices:
            raise RuntimeError("OpenAI returned no choices")

        msg = choices[0].get("message", {})
        content = msg.get("content", "")
        if isinstance(content, str):
            text = content.strip()
        elif isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(item.get("text", ""))
            text = "\n".join(parts).strip()
        else:
            text = ""

        if not text:
            finish_reason = choices[0].get("finish_reason")
            raise RuntimeError(f"OpenAI returned empty content (finish_reason={finish_reason})")
        return text

    def generate_text(self, prompt: str, model_name: str = "gemini-2.5-flash") -> str:
        if not prompt:
            raise ValueError("prompt is required")
        if not genai or not Config.GEMINI_API_KEY:
            raise RuntimeError("Gemini API key not configured")
        self._ensure_configured()
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        return (getattr(response, "text", "") or "").strip()

    def generate_lesson_text(self, prompt: str, max_completion_tokens: int = None) -> str:
        if not prompt:
            raise ValueError("prompt is required")
        max_tokens = Config.LESSON_MAX_COMPLETION_TOKENS if max_completion_tokens is None else int(max_completion_tokens)
        return self._call_openai_chat(
            prompt,
            model_name=Config.LESSON_GENERATION_MODEL,
            max_completion_tokens=max_tokens,
        )


ai_service = AIService()
