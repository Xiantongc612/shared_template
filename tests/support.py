import os
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol

ROOT = Path(__file__).parents[1]

SHARED_FILES = {
    ".copier-answers.yml",
    ".gitignore",
    ".pre-commit-config.yaml",
    "AGENTS.md",
    "README.md",
    "devbox.json",
}
WORKFLOW_FILES = {"auto-merge.yml", "release.yml", "validate.yml"}
HISTORICAL_ANSWERS = ROOT / "tests" / "fixtures" / "historical-answers.yml"
HISTORICAL_TEMPLATE_COMMIT = "b3806641460b9f1b7d15a6c7987a0879c8dfd936"


class Render(Protocol):
    def __call__(self, name: str, answers: Mapping[str, Any] | None = None) -> Path: ...


def git(path: Path, *arguments: str) -> None:
    environment = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Template Tests",
        "GIT_AUTHOR_EMAIL": "template-tests@example.invalid",
        "GIT_COMMITTER_NAME": "Template Tests",
        "GIT_COMMITTER_EMAIL": "template-tests@example.invalid",
    }
    result = subprocess.run(
        [
            "git",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "tag.gpgSign=false",
            *arguments,
        ],
        cwd=path,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
