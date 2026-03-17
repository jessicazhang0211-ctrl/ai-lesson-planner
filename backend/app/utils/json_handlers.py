import json


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
