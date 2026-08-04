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

    assert devbox["packages"] == [
        "gitleaks@8.30.1",
        "pre-commit@4.5.1",
        "bun@1.3.13",
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
