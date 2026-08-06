import re

import yaml
from support import ROOT


def test_repository_semgrep_config_is_parseable() -> None:
    config = yaml.safe_load((ROOT / "semgrep.yml").read_text())

    assert config["rules"]
    assert all(rule["id"] for rule in config["rules"])
    assert all(rule["message"] for rule in config["rules"])
    assert all(rule["severity"] for rule in config["rules"])


def test_repository_semgrep_rules_have_supported_languages() -> None:
    config = yaml.safe_load((ROOT / "semgrep.yml").read_text())

    supported = {"python", "yaml", "json", "generic", "ts", "javascript", "rust", "hcl"}
    for rule in config["rules"]:
        languages = rule.get("languages")
        if languages is not None:
            assert set(languages) <= supported


def test_repository_semgrep_config_is_committed_and_pinned() -> None:
    devbox = (ROOT / "devbox.json").read_text()
    semgrep = re.search(r"semgrep@(\S+)", devbox)
    assert semgrep, "semgrep package is not pinned in the repository devbox.json"
    assert semgrep.group(1) != "latest"
    assert (ROOT / "semgrep.yml").is_file()


def test_repository_semgrepignore_keeps_test_sources() -> None:
    ignores = (ROOT / ".semgrepignore").read_text()

    assert "tests" not in ignores.splitlines()
    assert "test_" not in ignores
    assert "template/**" in ignores


def test_generated_semgrep_is_component_aware(render) -> None:
    rules = {}
    for name, answers in {
        "React": {"components": ["frontend"], "frontend_variant": "react"},
        "Astro": {"components": ["frontend"], "frontend_variant": "astro"},
        "Tauri": {"components": ["client"]},
        "Hono": {"components": ["backend"], "backend_variants": ["hono"]},
        "FastAPI": {"components": ["backend"], "backend_variants": ["fastapi"]},
        "Scripts": {"components": ["scripts"]},
        "Everything": {
            "components": ["frontend", "client", "backend"],
            "backend_variants": ["hono", "fastapi"],
        },
    }.items():
        project = render(name, answers)
        config = yaml.safe_load((project / "semgrep.yml").read_text())
        rules[name] = {rule["id"] for rule in config["rules"]}

    assert "typescript-shell-injection" in rules["React"]
    assert "hcl-hardcoded-credentials" in rules["Astro"]
    assert "rust-shell-injection" in rules["Tauri"]
    assert "hcl-hardcoded-credentials" in rules["Hono"]
    assert "python-shell-injection" in rules["FastAPI"]
    assert "python-shell-injection" in rules["Scripts"]
    assert "python-eval-exec" in rules["Scripts"]
    assert "rust-shell-injection" in rules["Everything"]
    assert "python-shell-injection" in rules["Everything"]

    assert "rust-shell-injection" not in rules["React"]
    assert "python-shell-injection" not in rules["React"]
    assert "rust-shell-injection" not in rules["FastAPI"]
    assert "typescript-shell-injection" not in rules["FastAPI"]
    assert "typescript-shell-injection" not in rules["Scripts"]
    assert "rust-shell-injection" not in rules["Scripts"]


def test_generated_semgrep_rules_are_parseable(render) -> None:
    project = render(
        "SemgrepParsing",
        {
            "components": ["frontend", "client", "backend"],
            "backend_variants": ["hono", "fastapi"],
        },
    )
    config = yaml.safe_load((project / "semgrep.yml").read_text())

    assert config["rules"]
    assert all(rule["id"] for rule in config["rules"])
    assert all(rule["message"] for rule in config["rules"])
    assert all(rule["severity"] for rule in config["rules"])
