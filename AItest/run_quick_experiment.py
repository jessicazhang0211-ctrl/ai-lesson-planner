import os
import run_experiments

# Quick experiment defaults (can still be overridden by shell env)
os.environ.setdefault("EXPERIMENT_MAX_TASKS", "1")
os.environ.setdefault("EXPERIMENT_TIMEOUT_SECONDS", "25")
os.environ.setdefault(
    "EXPERIMENT_MODEL_ALLOWLIST",
    "Gemini 2.5 Flash,deepseek-chat,qwen3.5-flash",
)

if __name__ == "__main__":
    run_experiments.main()
