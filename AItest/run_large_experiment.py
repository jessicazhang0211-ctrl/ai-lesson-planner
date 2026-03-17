import os
import run_experiments

# Large-scale profile: 36 tasks
# To keep runtime practical and stable, use one fast core model with 3 conditions.
os.environ["EXPERIMENT_RUN_TAG"] = "large"
os.environ["EXPERIMENT_MAX_TASKS"] = "36"
os.environ["EXPERIMENT_TIMEOUT_SECONDS"] = "30"
os.environ["EXPERIMENT_MODEL_ALLOWLIST"] = "Gemini 2.5 Flash"

if __name__ == "__main__":
    run_experiments.main()
