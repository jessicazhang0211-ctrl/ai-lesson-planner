import random
import re
from typing import Any, Dict, List


def suggest_difficulty_ratio(class_accuracy: float) -> Dict[str, float]:
    acc = float(class_accuracy or 0.0)
    if acc >= 0.85:
        return {"easy": 0.2, "medium": 0.5, "hard": 0.3}
    if acc >= 0.7:
        return {"easy": 0.3, "medium": 0.5, "hard": 0.2}
    if acc >= 0.55:
        return {"easy": 0.45, "medium": 0.4, "hard": 0.15}
    return {"easy": 0.6, "medium": 0.3, "hard": 0.1}


def _replace_numbers(text: str, delta_range: tuple = (-3, 3)) -> str:
    def repl(match):
        n = int(match.group(0))
        d = random.randint(delta_range[0], delta_range[1])
        if d == 0:
            d = 1
        return str(max(1, n + d))

    return re.sub(r"\b\d+\b", repl, text or "")


def generate_isomorphic_variants(mother: Dict[str, Any], count: int = 3) -> List[Dict[str, Any]]:
    count = max(1, int(count or 1))
    stem = str(mother.get("stem") or mother.get("question") or "")
    answer = str(mother.get("answer") or "")
    scenario = str(mother.get("scenario") or "")

    variants = []
    for i in range(count):
        v_stem = _replace_numbers(stem)
        v_answer = _replace_numbers(answer)
        v_scenario = _replace_numbers(scenario)
        variants.append(
            {
                "id": f"variant_{i + 1}",
                "stem": v_stem,
                "answer": v_answer,
                "scenario": v_scenario,
                "transformation": "numeric-substitution",
            }
        )
    return variants
