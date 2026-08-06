from pathlib import Path

import yaml
from support import ROOT, Render

FETCH_METADATA_SHA = "25dd0e34f4fe68f24cc83900b1fe3fe149efef98"
FETCH_METADATA_REF = f"dependabot/fetch-metadata@{FETCH_METADATA_SHA}"
FETCH_METADATA_PIN = f"{FETCH_METADATA_REF} # v3.1.0"


def dependabot_entries(project: Path) -> set[tuple[str, str]]:
    config = yaml.safe_load((project / ".github" / "dependabot.yml").read_text())
    return {
        (update["package-ecosystem"], update["directory"])
        for update in config["updates"]
    }


def test_repository_dependabot_covers_actions_python_and_pre_commit() -> None:
    config = yaml.safe_load((ROOT / ".github" / "dependabot.yml").read_text())

    assert dependabot_entries(ROOT) == {
        ("github-actions", "/"),
        ("pre-commit", "/"),
        ("uv", "/"),
    }
    assert all(
        update["schedule"]["interval"] == "daily" for update in config["updates"]
    )


def test_rendered_dependabot_tracks_selected_components(render: Render) -> None:
    default = render("Default")
    client = render("Client", {"components": ["client"]})
    hono = render("Hono", {"components": ["backend"], "backend_variants": ["hono"]})
    scripts = render("Scripts", {"components": ["scripts"]})
    everything = render(
        "Everything",
        {
            "frontend_variant": "astro",
            "components": ["frontend", "client", "backend"],
            "backend_variants": ["hono", "fastapi"],
        },
    )

    assert dependabot_entries(default) == {
        ("github-actions", "/"),
        ("bun", "/frontend"),
    }
    assert dependabot_entries(client) == {
        ("github-actions", "/"),
        ("bun", "/client"),
        ("cargo", "/client/src-tauri"),
    }
    assert dependabot_entries(hono) == {
        ("github-actions", "/"),
        ("bun", "/backend/hono"),
        ("opentofu", "/backend/hono/infrastructure"),
    }
    assert dependabot_entries(scripts) == {
        ("github-actions", "/"),
        ("uv", "/scripts"),
    }
    assert dependabot_entries(everything) == {
        ("github-actions", "/"),
        ("bun", "/frontend"),
        ("bun", "/client"),
        ("bun", "/backend/hono"),
        ("cargo", "/client/src-tauri"),
        ("uv", "/backend/fastapi"),
        ("opentofu", "/frontend/infrastructure"),
        ("opentofu", "/backend/hono/infrastructure"),
    }


def test_rendered_dependabot_uses_weekly_schedule(render: Render) -> None:
    project = render(
        "Scheduled",
        {
            "components": ["frontend", "client", "backend"],
            "backend_variants": ["hono", "fastapi"],
        },
    )
    config = yaml.safe_load((project / ".github" / "dependabot.yml").read_text())

    assert all(
        update["schedule"]["interval"] == "weekly" for update in config["updates"]
    )
    assert all(
        update["open-pull-requests-limit"] == 5
        if update["package-ecosystem"] == "github-actions"
        else update["open-pull-requests-limit"] == 3
        for update in config["updates"]
    )


def test_repository_auto_merge_is_guarded_and_pinned() -> None:
    workflow = yaml.safe_load(
        (ROOT / ".github" / "workflows" / "auto-merge.yml").read_text()
    )
    job = workflow["jobs"]["auto-merge"]
    steps = job["steps"]

    assert workflow[True] == {
        "pull_request_target": {"types": ["opened", "synchronize"]}
    }
    assert job["if"] == "github.actor == 'dependabot[bot]'"
    assert job["runs-on"] == "ubuntu-24.04"
    assert job["timeout-minutes"] == 10
    assert steps[0]["uses"] == FETCH_METADATA_REF
    assert (
        FETCH_METADATA_PIN
        in (ROOT / ".github" / "workflows" / "auto-merge.yml").read_text()
    )
    assert (
        steps[1]["if"]
        == "steps.metadata.outputs.update-type == 'version-update:semver-patch'"
    )


def test_rendered_auto_merge_is_guarded_and_pinned(render: Render) -> None:
    project = render("AutoMerge")
    workflow = yaml.safe_load(
        (project / ".github" / "workflows" / "auto-merge.yml").read_text()
    )
    job = workflow["jobs"]["auto-merge"]
    steps = job["steps"]

    assert workflow[True] == {
        "pull_request_target": {"types": ["opened", "synchronize"]}
    }
    assert job["if"] == "github.actor == 'dependabot[bot]'"
    assert job["runs-on"] == "ubuntu-24.04"
    assert job["timeout-minutes"] == 10
    assert steps[0]["uses"] == FETCH_METADATA_REF
    assert (
        FETCH_METADATA_PIN
        in (project / ".github" / "workflows" / "auto-merge.yml").read_text()
    )
    assert (
        steps[1]["if"]
        == "steps.metadata.outputs.update-type == 'version-update:semver-patch'"
    )
