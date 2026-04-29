import json
import re
from typing import Any, Callable, Dict, Optional


def extract_json(text: str):
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(cleaned)
    except Exception:
        pass

    obj_start = cleaned.find("{")
    obj_end = cleaned.rfind("}")
    if obj_start != -1 and obj_end != -1 and obj_end > obj_start:
        try:
            return json.loads(cleaned[obj_start:obj_end + 1])
        except Exception:
            pass

    arr_start = cleaned.find("[")
    arr_end = cleaned.rfind("]")
    if arr_start != -1 and arr_end != -1 and arr_end > arr_start:
        try:
            return json.loads(cleaned[arr_start:arr_end + 1])
        except Exception:
            pass

    return None


def safe_json_loads(raw: str, default):
    try:
        return json.loads(raw) if raw else default
    except Exception:
        return default


def _try_json_loads(text: str):
    try:
        return json.loads(text)
    except Exception:
        return None


def _extract_json_from_code_fence(text: str):
    pattern = re.compile(r"```(?:json|JSON)?\s*([\s\S]*?)\s*```", re.MULTILINE)
    for block in pattern.findall(text or ""):
        obj = _try_json_loads((block or "").strip())
        if obj is not None:
            return obj
    return None


def _extract_json_object_or_array(text: str):
    cleaned = (text or "").strip()
    obj_start = cleaned.find("{")
    obj_end = cleaned.rfind("}")
    if obj_start != -1 and obj_end != -1 and obj_end > obj_start:
        obj = _try_json_loads(cleaned[obj_start : obj_end + 1])
        if obj is not None:
            return obj

    arr_start = cleaned.find("[")
    arr_end = cleaned.rfind("]")
    if arr_start != -1 and arr_end != -1 and arr_end > arr_start:
        arr = _try_json_loads(cleaned[arr_start : arr_end + 1])
        if arr is not None:
            return arr
    return None


def extract_json_three_stage(
    text: str,
    llm_cleaner: Optional[Callable[[str], str]] = None,
) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "value": None,
        "stage": "failed",
        "notes": [],
    }

    cleaned = (text or "").strip()
    if not cleaned:
        result["notes"].append("empty_output")
        return result

    direct = _try_json_loads(cleaned)
    if direct is not None:
        result["value"] = direct
        result["stage"] = "direct"
        return result

    result["notes"].append("direct_parse_failed")

    fenced = _extract_json_from_code_fence(cleaned)
    if fenced is not None:
        result["value"] = fenced
        result["stage"] = "code_fence"
        return result

    snippet = _extract_json_object_or_array(cleaned)
    if snippet is not None:
        result["value"] = snippet
        result["stage"] = "snippet"
        return result

    result["notes"].append("regex_extract_failed")

    if llm_cleaner is not None:
        try:
            repaired = llm_cleaner(cleaned)
            repaired_obj = _try_json_loads((repaired or "").strip())
            if repaired_obj is None:
                repaired_obj = _extract_json_object_or_array(repaired or "")
            if repaired_obj is not None:
                result["value"] = repaired_obj
                result["stage"] = "llm_clean"
                return result
            result["notes"].append("llm_clean_parse_failed")
        except Exception as e:
            result["notes"].append(f"llm_clean_error:{type(e).__name__}")

    return result
