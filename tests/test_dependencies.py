import json
import re
import tomllib

from support import Render


def test_generated_direct_dependencies_are_exact_without_lockfiles(
    render: Render,
) -> None:
    answers = {
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
    }
    project = render("ExactDependencies", answers)
    astro = render(
        "ExactAstroDependencies",
        {
            "frontend_variant": "astro",
            "frontend_playwright": True,
            "frontend_ai_sdk": True,
            "frontend_i18next": True,
        },
    )
    exact_version = re.compile(r"^\d+(?:\.\d+)+(?:[-+][0-9A-Za-z.-]+)?$")

    for path in (
        project / "frontend" / "package.json",
        project / "client" / "package.json",
        project / "backend" / "hono" / "package.json",
        astro / "frontend" / "package.json",
    ):
        package = json.loads(path.read_text())
        dependencies = package.get("dependencies", {}) | package.get(
            "devDependencies", {}
        )
        assert all(
            exact_version.fullmatch(version) for version in dependencies.values()
        )

    fastapi = tomllib.loads(
        (project / "backend" / "fastapi" / "pyproject.toml").read_text()
    )
    assert all(
        "==" in requirement for requirement in fastapi["project"]["dependencies"]
    )
    assert all(
        "==" in requirement for requirement in fastapi["dependency-groups"]["dev"]
    )

    cargo = tomllib.loads((project / "client" / "src-tauri" / "Cargo.toml").read_text())
    cargo_versions = [
        cargo["build-dependencies"]["tauri-build"]["version"],
        cargo["dependencies"]["serde"]["version"],
        cargo["dependencies"]["serde_json"],
        cargo["dependencies"]["tauri"]["version"],
    ]
    assert all(version.startswith("=") for version in cargo_versions)
    assert all(exact_version.fullmatch(version[1:]) for version in cargo_versions)

    devbox = json.loads((project / "devbox.json").read_text())
    assert all("@latest" not in package for package in devbox["packages"])
    assert "python@3.14.4" in devbox["packages"]

    lockfiles = {
        ".terraform.lock.hcl",
        "devbox.lock",
        "bun.lock",
        "bun.lockb",
        "Cargo.lock",
        "uv.lock",
    }
    assert not any(path.name in lockfiles for path in project.rglob("*"))
    gitignore = (project / ".gitignore").read_text().splitlines()
    assert lockfiles <= set(gitignore)
