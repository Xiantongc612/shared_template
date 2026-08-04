from collections.abc import Mapping
from typing import Any

import pytest
import yaml
from support import SHARED_FILES, WORKFLOW_FILES, Render


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
    recorded_answers = yaml.safe_load((project / ".copier-answers.yml").read_text())
    expected_workflows = WORKFLOW_FILES.copy()
    if "cloudflare_project_id" in recorded_answers:
        expected_workflows.add("cloudflare-deploy.yml")

    assert SHARED_FILES <= {path.name for path in project.iterdir()}
    assert expected_workflows == {
        path.name for path in (project / ".github" / "workflows").iterdir()
    }
    assert all(
        isinstance(yaml.safe_load(path.read_text()), dict)
        for path in (project / ".github" / "workflows").iterdir()
    )
    assert all(text in readme for text in expected)
    assert all(text not in readme for text in unexpected)


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
        path.relative_to(second): path.read_bytes()
        .replace(b"Second", b"First")
        .replace(b"second", b"first")
        for path in second.rglob("*")
        if path.is_file()
    }
    assert first_files == second_files
