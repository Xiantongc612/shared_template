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
    "AGENTS.md",
    "README.md",
    "devbox.json",
}
WORKFLOW_FILES = {"build.yml", "check.yml", "release.yml", "test.yml"}


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

    assert SHARED_FILES <= {path.name for path in project.iterdir()}
    assert WORKFLOW_FILES == {
        path.name for path in (project / ".github" / "workflows").iterdir()
    }
    assert all(
        isinstance(yaml.safe_load(path.read_text()), dict)
        for path in (project / ".github" / "workflows").iterdir()
    )
    assert all(text in readme for text in expected)
    assert all(text not in readme for text in unexpected)


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


def test_root_commands_have_separate_responsibilities(render: Render) -> None:
    project = render(
        "Everything",
        {
            "components": ["frontend", "client", "backend"],
            "backend_variants": ["hono", "fastapi"],
            "frontend_playwright": True,
            "client_playwright": True,
        },
    )
    scripts = json.loads((project / "devbox.json").read_text())["shell"]["scripts"]

    assert scripts.keys() >= {"init", "fmt", "check", "test", "test:e2e", "build"}
    assert not any(
        " test" in command or "pytest" in command for command in scripts["check"]
    )
    assert not any(" build" in command for command in scripts["check"])
    assert not any("build" in command for command in scripts["test"])
    assert any("ruff format backend/fastapi" in command for command in scripts["fmt"])
    assert any("cargo fmt" in command for command in scripts["fmt"])
    assert any("cargo fmt" in command for command in scripts["check"])
    assert any("cargo check" in command for command in scripts["check"])
    assert any("cargo clippy" in command for command in scripts["check"])
    assert any("cargo test" in command for command in scripts["test"])
    assert len(scripts["test:e2e"]) == 2
    assert any("docker buildx build" in command for command in scripts["build"])


def test_astro_only_test_is_a_successful_noop(render: Render) -> None:
    project = render("Astro", {"frontend_variant": "astro"})
    scripts = json.loads((project / "devbox.json").read_text())["shell"]["scripts"]

    assert scripts["test"] == ["echo 'No unit tests configured.'"]
    assert "test:e2e" not in scripts


def test_generated_agents_only_describes_selected_components(render: Render) -> None:
    project = render(
        "FastAPI",
        {"components": ["backend"], "backend_variants": ["fastapi"]},
    )
    instructions = (project / "AGENTS.md").read_text()

    assert "FastAPI Backend" in instructions
    assert "React Frontend" not in instructions
    assert "Astro Frontend" not in instructions
    assert "Tauri Client" not in instructions
    assert "Hono Backend" not in instructions


def test_workflows_use_separate_commands_and_least_privilege(render: Render) -> None:
    project = render("Default")
    workflows = project / ".github" / "workflows"
    check = (workflows / "check.yml").read_text()
    test = (workflows / "test.yml").read_text()
    build = (workflows / "build.yml").read_text()
    release = (workflows / "release.yml").read_text()

    assert "devbox run check" in check
    assert "devbox run test" not in check
    assert "devbox run build" not in check
    assert "devbox run test" in test
    assert "test-e2e:" not in test
    assert "devbox run build" in build
    assert "contents: read" in check
    assert "contents: read" in test
    assert "contents: read" in build
    assert "contents: write" in release
    assert "GH_TOKEN: ${{ github.token }}" in release
    assert 'tags:\n      - "v*"' in release
    assert "frontend.tar.gz" in release
    assert "wrangler deploy" not in release
    assert "docker push" not in release


def test_all_component_workflows_are_conditional_and_linux_only(render: Render) -> None:
    project = render(
        "Everything",
        {
            "components": ["frontend", "client", "backend"],
            "backend_variants": ["hono", "fastapi"],
            "frontend_playwright": True,
            "client_playwright": True,
        },
    )
    workflows = project / ".github" / "workflows"
    all_text = "\n".join(path.read_text() for path in workflows.iterdir())
    test = (workflows / "test.yml").read_text()
    release = (workflows / "release.yml").read_text()

    assert "test-e2e:" in test
    assert test.count("playwright install --with-deps chromium") == 2
    assert "macos-" not in all_text
    assert "windows-" not in all_text
    assert "ubuntu-22.04" in all_text
    assert "*.deb" in release
    assert "*.AppImage" in release
    assert "hono-worker.tar.gz" in release
    assert "fastapi-backend.tar" in release


def test_fastapi_workflows_omit_unselected_runtime_setup(render: Render) -> None:
    project = render(
        "FastAPI",
        {"components": ["backend"], "backend_variants": ["fastapi"]},
    )
    all_text = "\n".join(
        path.read_text() for path in (project / ".github" / "workflows").iterdir()
    )

    assert "Tauri" not in all_text
    assert "playwright" not in all_text
    assert "frontend.tar.gz" not in all_text
    assert "hono-worker.tar.gz" not in all_text
    assert "fastapi-backend.tar" in all_text


def test_react_integrations_are_independently_rendered(render: Render) -> None:
    project = render(
        "ReactAI",
        {"frontend_ai_sdk": True},
    )
    package = json.loads((project / "frontend" / "package.json").read_text())

    assert package["dependencies"]["ai"] == "7.0.48"
    assert "@tanstack/react-query" not in package["dependencies"]
    assert "i18next" not in package["dependencies"]
    assert "@playwright/test" not in package["devDependencies"]
    assert (project / "frontend" / "src" / "integrations" / "ai.ts").is_file()
    assert not (project / "frontend" / "playwright.config.ts").exists()


def test_react_all_integrations_render_configuration(render: Render) -> None:
    project = render(
        "ReactAll",
        {
            "frontend_playwright": True,
            "frontend_ai_sdk": True,
            "frontend_tanstack_query": True,
            "frontend_i18next": True,
        },
    )
    frontend = project / "frontend"
    package = json.loads((frontend / "package.json").read_text())

    assert {
        "ai",
        "zod",
        "@tanstack/react-query",
        "i18next",
        "react-i18next",
    } <= package["dependencies"].keys()
    assert package["devDependencies"]["@playwright/test"] == "1.62.1"
    assert (frontend / "playwright.config.ts").is_file()
    assert (frontend / "e2e" / "app.spec.ts").is_file()
    assert (frontend / "src" / "integrations" / "ai.ts").is_file()
    assert (frontend / "src" / "integrations" / "i18n.ts").is_file()
    assert "QueryClientProvider" in (frontend / "src" / "main.tsx").read_text()


def test_react_files_are_absent_without_react_variant(render: Render) -> None:
    client = render("ClientOnly", {"components": ["client"]})
    astro = render("AstroOnly", {"frontend_variant": "astro"})

    assert not (client / "frontend").exists()
    assert not (astro / "frontend" / "src" / "App.tsx").exists()


def test_astro_generator_is_independent(render: Render) -> None:
    project = render(
        "AstroAll",
        {
            "frontend_variant": "astro",
            "frontend_playwright": True,
            "frontend_ai_sdk": True,
            "frontend_i18next": True,
        },
    )
    frontend = project / "frontend"
    package = json.loads((frontend / "package.json").read_text())

    assert package["dependencies"]["astro"] == "7.1.6"
    assert package["dependencies"]["ai"] == "7.0.48"
    assert package["dependencies"]["i18next"] == "26.3.6"
    assert "react" not in package["dependencies"]
    assert "@tanstack/react-query" not in package["dependencies"]
    assert (frontend / "src" / "pages" / "index.astro").is_file()
    assert not (frontend / "src" / "App.tsx").exists()
    assert (frontend / "playwright.config.ts").is_file()


def test_client_generator_is_independent(render: Render) -> None:
    project = render(
        "ClientAll",
        {
            "components": ["client"],
            "client_playwright": True,
            "client_ai_sdk": True,
            "client_tanstack_query": True,
            "client_i18next": True,
        },
    )
    client = project / "client"
    package = json.loads((client / "package.json").read_text())

    assert package["dependencies"]["@tauri-apps/api"] == "2.11.1"
    assert "ai" in package["dependencies"]
    assert "@tanstack/react-query" in package["dependencies"]
    assert "i18next" in package["dependencies"]
    assert (client / "src-tauri" / "tauri.conf.json").is_file()
    assert (client / "src-tauri" / "src" / "lib.rs").is_file()
    assert not (project / "frontend").exists()


def test_hono_generator_and_optional_ai(render: Render) -> None:
    project = render(
        "HonoAI",
        {
            "components": ["backend"],
            "backend_variants": ["hono"],
            "hono_ai_sdk": True,
        },
    )
    service = project / "backend" / "hono"
    package = json.loads((service / "package.json").read_text())

    assert package["dependencies"]["hono"] == "4.12.34"
    assert package["dependencies"]["ai"] == "7.0.48"
    assert (service / "wrangler.jsonc").is_file()
    assert (service / "src" / "ai.ts").is_file()
    assert not (project / "backend" / "fastapi").exists()


def test_fastapi_generator_and_optional_ai(render: Render) -> None:
    project = render(
        "FastAPIAI",
        {
            "components": ["backend"],
            "backend_variants": ["fastapi"],
            "fastapi_pydantic_ai": True,
        },
    )
    service = project / "backend" / "fastapi"
    pyproject = (service / "pyproject.toml").read_text()

    assert "fastapi==0.141.1" in pyproject
    assert "pydantic-ai==2.22.0" in pyproject
    assert (service / "Dockerfile").is_file()
    assert (service / "app" / "ai.py").is_file()
    assert not (project / "backend" / "hono").exists()


def test_all_components_have_independent_boundaries(render: Render) -> None:
    project = render(
        "FullStack",
        {
            "components": ["frontend", "client", "backend"],
            "backend_variants": ["hono", "fastapi"],
        },
    )

    assert (project / "frontend" / "package.json").is_file()
    assert (project / "client" / "package.json").is_file()
    assert (project / "client" / "src-tauri" / "Cargo.toml").is_file()
    assert (project / "backend" / "hono" / "package.json").is_file()
    assert (project / "backend" / "fastapi" / "pyproject.toml").is_file()
    assert not (project / "docker-compose.yml").exists()
    assert not (project / "packages").exists()


def test_both_backends_do_not_share_manifests(render: Render) -> None:
    project = render(
        "Backends",
        {
            "components": ["backend"],
            "backend_variants": ["hono", "fastapi"],
        },
    )

    assert (project / "backend" / "hono" / "package.json").is_file()
    assert not (project / "backend" / "hono" / "pyproject.toml").exists()
    assert (project / "backend" / "fastapi" / "pyproject.toml").is_file()
    assert not (project / "backend" / "fastapi" / "package.json").exists()


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
    assert "uv@0.12.1" in devbox
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
