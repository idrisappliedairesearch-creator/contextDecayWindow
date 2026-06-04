import os

# Auto-load .env from project root
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.isfile(dotenv_path):
    with open(dotenv_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

from src.study.runner import StudyRunner

if __name__ == "__main__":
    runner = StudyRunner(
        script_path="experiments/study_001/script.json",
        study_dir="experiments/study_001/runs",
        run_id="run_001",
    )
    runner.run()
