import json
from pathlib import Path

BASE = Path(__file__).resolve().parent

REQUIRED_JSON_FILES = [
    "uk_primary_math_evaluation_rubric.json",
    "uk_primary_math_generation_request_example.json",
    "uk_primary_math_lesson_plan_schema.json",
    "uk_primary_math_model_guardrails.json",
    "uk_primary_math_model_test_matrix.json",
    "uk_primary_math_task_set_36.json",
]


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main():
    print("Validating AItest assets...")
    for name in REQUIRED_JSON_FILES:
        p = BASE / name
        if not p.exists():
            raise FileNotFoundError(f"Missing file: {name}")
        load_json(p)
        print(f"[OK] JSON parse: {name}")

    tasks = load_json(BASE / "uk_primary_math_task_set_36.json")
    task_items = tasks.get("tasks") or []
    if len(task_items) != 36:
        raise ValueError(f"Task count must be 36, got {len(task_items)}")

    ids = [x.get("task_id") for x in task_items]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate task_id found")

    matrix = load_json(BASE / "uk_primary_math_model_test_matrix.json")
    core_models = matrix.get("core_experiment_set") or []
    if len(core_models) < 8:
        raise ValueError("core_experiment_set should include at least 8 models")

    print(f"[OK] Task count: {len(task_items)}")
    print(f"[OK] Core models: {len(core_models)}")
    print("Validation completed.")


if __name__ == "__main__":
    main()
