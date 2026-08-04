import json

import yaml
from support import ROOT, Render


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
    docker_build = next(
        command for command in scripts["build"] if "docker buildx build" in command
    )
    assert "${DOCKER_CACHE_ARGS:-}" in docker_build

    packages = json.loads((project / "devbox.json").read_text())["packages"]
    assert "actionlint@1.7.12" in packages
    assert "actionlint" in scripts["check"]
    assert any(package.startswith("semgrep@") for package in packages)
    assert "semgrep scan --config semgrep.yml" in scripts["check"]


def test_astro_only_test_is_a_successful_noop(render: Render) -> None:
    project = render("Astro", {"frontend_variant": "astro"})
    scripts = json.loads((project / "devbox.json").read_text())["shell"]["scripts"]

    assert scripts["test"] == ["echo 'No unit tests configured.'"]
    assert "test:e2e" not in scripts


def test_repository_commands_enforce_uv_lock() -> None:
    scripts = json.loads((ROOT / "devbox.json").read_text())["shell"]["scripts"]

    assert "uv lock --check" in scripts["check"]
    assert "actionlint" in scripts["check"]
    assert "semgrep scan --config semgrep.yml" in scripts["check"]
    uv_commands = [
        command
        for commands in scripts.values()
        for command in commands
        if command.startswith("uv run")
    ]
    assert uv_commands
    assert all(command.startswith("uv run --locked ") for command in uv_commands)


def test_repository_pins_semgrep() -> None:
    devbox = json.loads((ROOT / "devbox.json").read_text())

    semgrep = next(
        package for package in devbox["packages"] if package.startswith("semgrep@")
    )
    assert semgrep.split("@", 1)[1] != "latest"
    assert (ROOT / "semgrep.yml").is_file()


def test_repository_tooling_versions_match_template(render: Render) -> None:
    root_devbox = json.loads((ROOT / "devbox.json").read_text())
    root_packages = {
        name: version
        for package in root_devbox["packages"]
        for name, _, version in (package.partition("@"),)
    }

    generated = json.loads((render("ToolingSync") / "devbox.json").read_text())[
        "packages"
    ]
    generated_packages = {
        name: version
        for package in generated
        for name, _, version in (package.partition("@"),)
    }

    shared = root_packages.keys() & generated_packages.keys()
    assert shared == {"actionlint", "bun", "gitleaks", "pre-commit", "semgrep"}
    assert all(root_packages[name] == generated_packages[name] for name in shared)


def test_repository_pre_commit_covers_check_steps() -> None:
    config = yaml.safe_load((ROOT / ".pre-commit-config.yaml").read_text())
    hook_ids = {hook["id"] for repo in config["repos"] for hook in repo["hooks"]}

    assert hook_ids >= {"gitleaks", "actionlint", "ruff", "ruff-format"}
