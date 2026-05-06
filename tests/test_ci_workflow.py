from pathlib import Path

import yaml


def test_ci_installs_local_project_with_dev_extras() -> None:
    workflow = yaml.safe_load(Path(".github/workflows/ci.yml").read_text(encoding="utf-8"))

    steps = workflow["jobs"]["test"]["steps"]
    run_commands = [step["run"] for step in steps if "run" in step]

    assert 'pip install -e ".[dev]"' in run_commands
    assert 'pip install -e "[dev]"' not in run_commands
