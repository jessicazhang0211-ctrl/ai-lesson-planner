import os
import run_experiments

# Report-required configuration from dissertation file:
# 36 tasks x 8 models x 3 conditions
os.environ["EXPERIMENT_RUN_TAG"] = "report_required"
os.environ["EXPERIMENT_MAX_TASKS"] = "36"
os.environ["EXPERIMENT_TIMEOUT_SECONDS"] = "30"
os.environ["EXPERIMENT_MODEL_ALLOWLIST"] = ",".join([
    "gpt-5.4",
    "gpt-5-mini",
    "Claude Opus 4.6",
    "Claude Sonnet 4.6",
    "Gemini 2.5 Pro",
    "Gemini 2.5 Flash",
    "deepseek-reasoner",
    "qwen3.5-plus",
])

if __name__ == "__main__":
    run_experiments.main()
