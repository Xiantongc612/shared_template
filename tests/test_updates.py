from pathlib import Path
from shutil import copy2, copytree
from typing import Any

import yaml
from copier import run_copy, run_update
from support import (
    HISTORICAL_ANSWERS,
    HISTORICAL_TEMPLATE_COMMIT,
    ROOT,
    WORKFLOW_FILES,
)
from support import git as _git


def test_copier_updates_answers_from_historical_commit(tmp_path: Path) -> None:
    source = tmp_path / "versioned-template"
    _git(tmp_path, "clone", "--quiet", str(ROOT), str(source))
    copy2(ROOT / "copier.yml", source)
    copytree(ROOT / "template", source / "template", dirs_exist_ok=True)
    _git(source, "add", "copier.yml", "template")
    _git(source, "commit", "--allow-empty", "-m", "current working template")
    historical_answers: dict[str, Any] = yaml.safe_load(HISTORICAL_ANSWERS.read_text())
    historical_answers["project_name"] = "Historical_App!"

    project = tmp_path / "project"
    run_copy(
        str(source),
        project,
        data=historical_answers,
        vcs_ref=HISTORICAL_TEMPLATE_COMMIT,
        defaults=True,
        quiet=True,
    )

    recorded_answers = yaml.safe_load((project / ".copier-answers.yml").read_text())
    assert {
        key: value for key, value in recorded_answers.items() if not key.startswith("_")
    } == historical_answers
    assert not (project / "AGENTS.md").exists()
    assert not (project / ".github").exists()

    _git(project, "init")
    _git(project, "add", ".")
    _git(project, "commit", "-m", "generated from historical template")

    run_update(
        project,
        vcs_ref="HEAD",
        defaults=True,
        overwrite=True,
        quiet=True,
    )

    updated_answers = yaml.safe_load((project / ".copier-answers.yml").read_text())
    assert {
        key: value for key, value in updated_answers.items() if not key.startswith("_")
    } == {
        **historical_answers,
        "cloudflare_project_id": "historical-app",
        "client_identifier": "com.example.historical-app",
    }
    tauri_config = yaml.safe_load(
        (project / "client" / "src-tauri" / "tauri.conf.json").read_text()
    )
    assert tauri_config["identifier"] == "com.example.historical-app"
    assert (project / "AGENTS.md").is_file()
    assert WORKFLOW_FILES | {"cloudflare-deploy.yml"} == {
        path.name for path in (project / ".github" / "workflows").iterdir()
    }
