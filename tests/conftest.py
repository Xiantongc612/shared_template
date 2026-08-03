from collections.abc import Mapping
from pathlib import Path
from shutil import copy2, copytree
from typing import Any, Protocol

import pytest
from copier import run_copy

ROOT = Path(__file__).parents[1]


class Render(Protocol):
    def __call__(self, name: str, answers: Mapping[str, Any] | None = None) -> Path: ...


@pytest.fixture
def template_path(tmp_path: Path) -> Path:
    destination = tmp_path / "template-source"
    destination.mkdir()
    copy2(ROOT / "copier.yml", destination)
    copytree(ROOT / "template", destination / "template")
    return destination


@pytest.fixture
def render(tmp_path: Path, template_path: Path) -> Render:
    def render_project(name: str, answers: Mapping[str, Any] | None = None) -> Path:
        destination = tmp_path / name
        run_copy(
            str(template_path),
            destination,
            data={"project_name": name, **(answers or {})},
            defaults=True,
            quiet=True,
        )
        return destination

    return render_project
