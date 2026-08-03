import json
import os
import subprocess
from collections.abc import Mapping
from pathlib import Path
from shutil import copy2, copytree
from typing import Any

import pytest
import yaml
from conftest import ROOT, Render
from copier import run_copy, run_update

SHARED_FILES = {
    ".copier-answers.yml",
    ".gitignore",
    ".pre-commit-config.yaml",
    "README.md",
    "devbox.json",
}


@pytest.mark.parametrize(
    ("name", "answers", "expected", "unexpected"),
    [
        ("React", {}, {"Frontend: React"}, {"Astro", "Tauri", "Hono", "FastAPI"}),
        (
            "Astro",
            {"frontend_variant": "astro"},
            {"Frontend: Astro"},
            {"React", "TanStack Query", "Tauri", "Hono", "FastAPI"},
        ),
        (
            "Client",
            {"components": ["client"]},
            {"Client: Tauri desktop application"},
            {"Frontend:", "Hono", "FastAPI"},
        ),
        (
            "Hono",
            {"components": ["backend"], "backend_variants": ["hono"]},
            {"Backend: Hono", "Cloudflare edge function"},
            {"Frontend:", "Tauri", "FastAPI", "OCI-compatible"},
        ),
        (
            "FastAPI",
            {"components": ["backend"], "backend_variants": ["fastapi"]},
            {"Backend: FastAPI", "OCI-compatible container"},
            {"Frontend:", "Tauri", "Hono", "Cloudflare"},
        ),
        (
            "Backends",
            {
                "components": ["backend"],
                "backend_variants": ["hono", "fastapi"],
            },
            {"Backend: Hono", "Backend: FastAPI"},
            {"Frontend:", "Tauri"},
        ),
        (
            "WebDesktop",
            {"components": ["frontend", "client"]},
            {"Frontend: React", "Client: Tauri desktop application"},
            {"Hono", "FastAPI"},
        ),
        (
            "Everything",
            {
                "components": ["frontend", "client", "backend"],
                "backend_variants": ["hono", "fastapi"],
                "frontend_playwright": True,
                "frontend_ai_sdk": True,
                "frontend_tanstack_query": True,
                "frontend_i18next": True,
                "client_playwright": True,
                "client_ai_sdk": True,
                "client_tanstack_query": True,
                "client_i18next": True,
                "hono_ai_sdk": True,
                "fastapi_pydantic_ai": True,
            },
            {
                "Frontend: React",
                "Client: Tauri desktop application",
                "Backend: Hono",
                "Backend: FastAPI",
                "Frontend: Playwright",
                "Frontend: AI SDK",
                "Frontend: TanStack Query",
                "Frontend: i18next",
                "Client: Playwright",
                "Client: AI SDK",
                "Client: TanStack Query",
                "Client: i18next",
                "Hono: AI SDK",
                "FastAPI: PydanticAI",
            },
            set(),
        ),
    ],
)
def test_render_matrix(
    render: Render,
    name: str,
    answers: Mapping[str, Any],
    expected: set[str],
    unexpected: set[str],
) -> None:
    project = render(name, answers)
    readme = (project / "README.md").read_text()

    assert {path.name for path in project.iterdir()} == SHARED_FILES
    assert all(text in readme for text in expected)
    assert all(text not in readme for text in unexpected)


def test_default_render_has_only_react_runtime(render: Render) -> None:
    project = render("Default")
    devbox = json.loads((project / "devbox.json").read_text())
    answers = yaml.safe_load((project / ".copier-answers.yml").read_text())

    assert devbox["packages"] == [
        "gitleaks@latest",
        "pre-commit@latest",
        "bun@latest",
    ]
    assert answers["components"] == ["frontend"]
    assert answers["frontend_variant"] == "react"
    assert not any(
        answers[key]
        for key in (
            "frontend_playwright",
            "frontend_ai_sdk",
            "frontend_tanstack_query",
            "frontend_i18next",
        )
    )
    assert "backend_variants" not in answers
    assert "client_playwright" not in answers


def test_frontend_and_client_answers_are_independent(render: Render) -> None:
    project = render(
        "Independent",
        {
            "components": ["frontend", "client"],
            "frontend_ai_sdk": True,
            "client_ai_sdk": False,
        },
    )
    readme = (project / "README.md").read_text()
    answers = yaml.safe_load((project / ".copier-answers.yml").read_text())

    assert "Frontend: AI SDK" in readme
    assert "Client: AI SDK" not in readme
    assert answers["frontend_ai_sdk"] is True
    assert answers["client_ai_sdk"] is False


def test_unselected_runtimes_leave_no_residue(render: Render) -> None:
    project = render(
        "FastAPIOnly",
        {"components": ["backend"], "backend_variants": ["fastapi"]},
    )
    devbox = (project / "devbox.json").read_text()
    gitignore = (project / ".gitignore").read_text()
    all_text = "\n".join(
        path.read_text() for path in project.iterdir() if path.is_file()
    )

    assert "python@3.14" in devbox
    assert "uv@latest" in devbox
    assert "bun" not in all_text
    assert "cargo" not in all_text
    assert "rustc" not in all_text
    assert "node_modules" not in gitignore
    assert ".venv/" in gitignore


@pytest.mark.parametrize(
    ("answers", "message"),
    [
        ({"project_name": "   "}, "Project name must not be empty."),
        (
            {"project_name": "Invalid", "components": []},
            "Select at least one of Frontend, Client, or Backend.",
        ),
        (
            {
                "project_name": "Invalid",
                "components": ["backend"],
                "backend_variants": [],
            },
            "Select at least one of Hono or FastAPI when Backend is selected.",
        ),
    ],
)
def test_invalid_answers_are_rejected(
    template_path: Path,
    tmp_path: Path,
    answers: dict[str, Any],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        run_copy(
            str(template_path),
            tmp_path / "invalid",
            data=answers,
            defaults=True,
            quiet=True,
        )


def test_astro_omits_tanstack_question_answer(render: Render) -> None:
    project = render(
        "Astro",
        {"frontend_variant": "astro", "frontend_tanstack_query": True},
    )
    answers = yaml.safe_load((project / ".copier-answers.yml").read_text())

    assert "frontend_tanstack_query" not in answers
    assert "TanStack Query" not in (project / "README.md").read_text()


def test_rendering_is_deterministic(render: Render) -> None:
    answers = {
        "components": ["frontend", "client", "backend"],
        "backend_variants": ["hono", "fastapi"],
    }
    first = render("First", answers)
    second = render("Second", answers)

    first_files = {
        path.relative_to(first): path.read_bytes()
        for path in first.rglob("*")
        if path.is_file()
    }
    second_files = {
        path.relative_to(second): path.read_bytes().replace(b"Second", b"First")
        for path in second.rglob("*")
        if path.is_file()
    }
    assert first_files == second_files


def test_copier_update_preserves_answers(tmp_path: Path) -> None:
    source = tmp_path / "versioned-template"
    source.mkdir()
    copy2(ROOT / "copier.yml", source)
    copytree(ROOT / "template", source / "template")
    _git(source, "init")
    _git(source, "add", ".")
    _git(source, "commit", "-m", "initial template")
    _git(source, "tag", "v1.0.0")

    project = tmp_path / "project"
    run_copy(
        str(source),
        project,
        data={"project_name": "Updated"},
        defaults=True,
        quiet=True,
    )
    _git(project, "init")
    _git(project, "add", ".")
    _git(project, "commit", "-m", "generated project")

    readme_template = source / "template" / "README.md.jinja"
    readme_template.write_text(readme_template.read_text() + "\nUpdate marker.\n")
    _git(source, "add", ".")
    _git(source, "commit", "-m", "update template")
    _git(source, "tag", "v1.1.0")

    run_update(project, defaults=True, overwrite=True, quiet=True)

    assert "Update marker." in (project / "README.md").read_text()
    answers = yaml.safe_load((project / ".copier-answers.yml").read_text())
    assert answers["project_name"] == "Updated"
    assert answers["components"] == ["frontend"]


def _git(path: Path, *arguments: str) -> None:
    environment = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Template Tests",
        "GIT_AUTHOR_EMAIL": "template-tests@example.invalid",
        "GIT_COMMITTER_NAME": "Template Tests",
        "GIT_COMMITTER_EMAIL": "template-tests@example.invalid",
    }
    result = subprocess.run(
        ["git", *arguments],
        cwd=path,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
