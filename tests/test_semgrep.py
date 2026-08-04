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
