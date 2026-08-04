import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from copier import run_copy
from support import Render


def test_default_render_has_only_react_runtime(render: Render) -> None:
    project = render("Default")
    devbox = json.loads((project / "devbox.json").read_text())
    answers = yaml.safe_load((project / ".copier-answers.yml").read_text())

    assert [package.partition("@")[0] for package in devbox["packages"]] == [
        "actionlint",
        "gitleaks",
        "semgrep",
        "pre-commit",
        "bun",
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
    assert (project / "frontend" / "package.json").is_file()


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
        (
            {
                "project_name": "Invalid",
                "frontend_variant": "astro",
                "cloudflare_project_id": "Invalid ID",
            },
            "Cloudflare project ID must use 1-46 lowercase letters",
        ),
        (
            {
                "project_name": "Invalid",
                "frontend_variant": "astro",
                "cloudflare_project_id": "a" * 47,
            },
            "Cloudflare project ID must use 1-46 lowercase letters",
        ),
        (
            {
                "project_name": "Invalid",
                "components": ["client"],
                "client_identifier": "Com.example.app",
            },
            "Client identifier must be at most 255 characters",
        ),
        (
            {
                "project_name": "Invalid",
                "components": ["client"],
                "client_identifier": "localhost",
            },
            "Client identifier must be at most 255 characters",
        ),
        (
            {
                "project_name": "Invalid",
                "components": ["client"],
                "client_identifier": "com.example.-app",
            },
            "Client identifier must be at most 255 characters",
        ),
        (
            {
                "project_name": "Invalid",
                "components": ["client"],
                "client_identifier": "com.example." + "a" * 244,
            },
            "Client identifier must be at most 255 characters",
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


@pytest.mark.parametrize(
    ("project_name", "expected_identifier"),
    [
        ("Desktop App!", "com.example.desktop-app"),
        ("!!!", "com.example.app"),
        ("a" * 300, "com.example." + "a" * 243),
        ("a" * 242 + "-remaining", "com.example." + "a" * 242),
    ],
)
def test_client_identifier_default_is_safe(
    render: Render, project_name: str, expected_identifier: str
) -> None:
    project = render(
        "ClientIdentifier",
        {"project_name": project_name, "components": ["client"]},
    )
    answers = yaml.safe_load((project / ".copier-answers.yml").read_text())
    tauri_config = json.loads(
        (project / "client" / "src-tauri" / "tauri.conf.json").read_text()
    )

    assert answers["client_identifier"] == expected_identifier
    assert tauri_config["identifier"] == expected_identifier
    assert len(expected_identifier) <= 255


def test_custom_client_identifier_is_rendered(render: Render) -> None:
    project = render(
        "CustomIdentifier",
        {
            "components": ["client"],
            "client_identifier": "io.example.desktop-app",
        },
    )
    answers = yaml.safe_load((project / ".copier-answers.yml").read_text())
    tauri_config = json.loads(
        (project / "client" / "src-tauri" / "tauri.conf.json").read_text()
    )

    assert answers["client_identifier"] == "io.example.desktop-app"
    assert tauri_config["identifier"] == "io.example.desktop-app"


def test_unselected_client_omits_identifier(render: Render) -> None:
    project = render("NoClient")
    answers = yaml.safe_load((project / ".copier-answers.yml").read_text())

    assert "client_identifier" not in answers
    assert not (project / "client").exists()
