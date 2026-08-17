import json
import re
import tomllib

from support import Render


def test_generated_direct_dependencies_are_exact_without_lockfiles(
    render: Render,
) -> None:
    answers = {
        "components": ["frontend", "client", "backend", "scripts", "kmp"],
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
        "python_data_analysis": True,
        "python_duckdb": True,
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

    scripts = tomllib.loads((project / "scripts" / "pyproject.toml").read_text())
    assert all(
        "==" in requirement for requirement in scripts["project"]["dependencies"]
    )
    assert all(
        "==" in requirement for requirement in scripts["dependency-groups"]["dev"]
    )
    assert scripts["project"]["scripts"] == {
        "utility-scripts": "utility_scripts.cli:main"
    }
    assert scripts["project"]["name"] == "utility-scripts"
    assert scripts["build-system"]["build-backend"] == "hatchling.build"

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
    assert any(package.startswith("python@") for package in devbox["packages"])
    assert "jetbrains.jdk-no-jcef-17@17.0.15-b1381" in devbox["packages"]
    assert "gradle@8.10.2" in devbox["packages"]
    semgrep = next(
        package for package in devbox["packages"] if package.startswith("semgrep@")
    )
    assert semgrep.split("@", 1)[1] != "latest"

    lockfiles = {
        ".terraform.lock.hcl",
        "devbox.lock",
        "bun.lock",
        "bun.lockb",
        "Cargo.lock",
        "uv.lock",
        "gradle.lockfile",
    }
    assert not any(path.name in lockfiles for path in project.rglob("*"))
    gitignore = (project / ".gitignore").read_text().splitlines()
    assert lockfiles <= set(gitignore)


def test_generated_versions_are_consistent_across_owned_files(render: Render) -> None:
    project = render(
        "VersionRelationships",
        {
            "components": ["frontend", "client", "backend", "scripts"],
            "backend_variants": ["hono", "fastapi"],
            "python_data_analysis": True,
            "python_duckdb": True,
        },
    )
    devbox = json.loads((project / "devbox.json").read_text())
    packages = {
        name: version
        for package in devbox["packages"]
        for name, _, version in (package.partition("@"),)
    }
    manifests = [
        json.loads((project / "frontend" / "package.json").read_text()),
        json.loads((project / "client" / "package.json").read_text()),
        json.loads((project / "backend" / "hono" / "package.json").read_text()),
    ]

    assert all(
        packages["bun"] == manifest["devDependencies"]["@types/bun"]
        for manifest in manifests
    )
    for component, manifest in zip(
        (project / "frontend", project / "client", project / "backend" / "hono"),
        manifests,
        strict=True,
    ):
        biome = json.loads((component / "biome.json").read_text())
        schema_version = biome["$schema"].split("/")[-2]
        assert schema_version == manifest["devDependencies"]["@biomejs/biome"]

    cargo = tomllib.loads((project / "client" / "src-tauri" / "Cargo.toml").read_text())
    tauri_version = cargo["dependencies"]["tauri"]["version"].removeprefix("=")
    assert tauri_version == manifests[1]["dependencies"]["@tauri-apps/api"]

    dockerfile = (project / "backend" / "fastapi" / "Dockerfile").read_text()
    assert f"ghcr.io/astral-sh/uv:{packages['uv']}@sha256:" in dockerfile
    assert f"python:{packages['python']}" in dockerfile
    assert (
        len(
            re.findall(
                r"^FROM .*@sha256:[0-9a-f]{64}(?: AS \w+)?$",
                dockerfile,
                re.MULTILINE,
            )
        )
        == 2
    )
    pre_commit = (project / ".pre-commit-config.yaml").read_text()
    assert f"rev: v{packages['gitleaks']}" in pre_commit

    fastapi_pyproject = tomllib.loads(
        (project / "backend" / "fastapi" / "pyproject.toml").read_text()
    )
    scripts_pyproject = tomllib.loads(
        (project / "scripts" / "pyproject.toml").read_text()
    )
    assert (
        scripts_pyproject["project"]["requires-python"]
        == fastapi_pyproject["project"]["requires-python"]
    )
    assert (
        scripts_pyproject["tool"]["ty"]["environment"]["python-version"]
        == fastapi_pyproject["tool"]["ty"]["environment"]["python-version"]
    )
    assert scripts_pyproject["project"]["dependencies"][0] == "duckdb==1.5.5"


def test_version_registry_is_not_generated(render: Render) -> None:
    project = render("RegistryExcluded")

    assert not (project / "_versions.jinja").exists()
    assert not any(path.name.startswith("_versions") for path in project.rglob("*"))
