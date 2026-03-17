import os
import run_experiments

# Middle-scale profile: 6 tasks x 3 models x 3 conditions
os.environ["EXPERIMENT_RUN_TAG"] = "middle"
os.environ["EXPERIMENT_MAX_TASKS"] = "6"
os.environ["EXPERIMENT_TIMEOUT_SECONDS"] = "30"
os.environ["EXPERIMENT_MODEL_ALLOWLIST"] = "Gemini 2.5 Flash,qwen3.5-flash,Claude Sonnet 4.6"

if __name__ == "__main__":
    run_experiments.main()
