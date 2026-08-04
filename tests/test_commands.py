import json

from support import Render


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
