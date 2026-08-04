import re
import subprocess
from pathlib import Path

import yaml
from support import ROOT, Render


def workflow_paths(project: Path) -> list[Path]:
    return sorted((project / ".github" / "workflows").glob("*.yml"))


def load_workflows(project: Path) -> dict[str, dict]:
    return {
        path.name: yaml.safe_load(path.read_text()) for path in workflow_paths(project)
    }


def test_repository_workflows_pin_runners_actions_and_devbox() -> None:
    workflow_text = "\n".join(
        path.read_text() for path in (ROOT / ".github" / "workflows").iterdir()
    )
    action_refs = re.findall(r"uses: ([^\s]+)", workflow_text)

    assert "ubuntu-latest" not in workflow_text
    assert action_refs
    assert all(re.search(r"@[0-9a-f]{40}$", ref) for ref in action_refs)
    assert "devbox-version: 0.17.5" in workflow_text
    assert "sha256-checksum:" in workflow_text
    assert "disable-nix-access-token: true" in workflow_text
    assert "persist-credentials: false" in workflow_text


def test_repository_release_workflow_publishes_template_on_version_tags() -> None:
    release = yaml.safe_load(
        (ROOT / ".github" / "workflows" / "release.yml").read_text()
    )

    assert release[True]["push"]["tags"] == ["v*"]
    jobs = release["jobs"]
    assert set(jobs) == {"prepare", "publish"}
    assert jobs["publish"]["needs"] == "prepare"
    assert jobs["prepare"]["permissions"]["contents"] == "read"
    assert jobs["publish"]["permissions"]["contents"] == "write"
    assert "gh release create" in jobs["publish"]["steps"][-1]["run"]


def test_rendered_workflows_pin_external_actions_and_devbox(render: Render) -> None:
    project = render(
        "Everything",
        {
            "components": ["frontend", "client", "backend"],
            "backend_variants": ["hono", "fastapi"],
            "frontend_playwright": True,
            "client_playwright": True,
        },
    )
    workflow_text = "\n".join(path.read_text() for path in workflow_paths(project))
    action_lines = re.findall(
        r"^\s*uses: (\S+)(?: # (\S+))?$", workflow_text, re.MULTILINE
    )

    assert action_lines
    assert all(re.fullmatch(r"[^@]+@[0-9a-f]{40}", ref) for ref, _ in action_lines)
    assert all(
        re.fullmatch(r"v\d+(?:\.\d+){0,2}", version) for _, version in action_lines
    )
    assert "devbox-version: 0.17.5" in workflow_text
    assert (
        "sha256-checksum: eb2d8fb34266ba3befc294d7d6f56e2cd4da2cacb7a0cf52db5b8092575544f8"
        in workflow_text
    )
    assert "disable-nix-access-token: true" in workflow_text
    assert workflow_text.count("persist-credentials: false") == workflow_text.count(
        "uses: actions/checkout@"
    )


def test_workflow_yaml_runners_timeouts_and_concurrency(render: Render) -> None:
    project = render(
        "Everything",
        {
            "components": ["frontend", "client", "backend"],
            "backend_variants": ["hono", "fastapi"],
            "frontend_variant": "astro",
            "frontend_playwright": True,
            "client_playwright": True,
        },
    )
    workflows = load_workflows(project)
    expected_timeouts = {
        ("check.yml", "check"): 60,
        ("test.yml", "test"): 60,
        ("test.yml", "test-e2e"): 60,
        ("build.yml", "build"): 90,
        ("release.yml", "prepare"): 120,
        ("release.yml", "publish"): 10,
        ("cloudflare-deploy.yml", "deploy"): 60,
    }

    assert workflows.keys() == {
        "build.yml",
        "check.yml",
        "cloudflare-deploy.yml",
        "release.yml",
        "test.yml",
    }
    for workflow_name, workflow in workflows.items():
        assert isinstance(workflow, dict)
        for job_name, job in workflow["jobs"].items():
            assert job["runs-on"] == "ubuntu-22.04"
            assert (
                job["timeout-minutes"] == expected_timeouts[(workflow_name, job_name)]
            )

    for workflow_name in ("check.yml", "test.yml", "build.yml"):
        assert workflows[workflow_name]["concurrency"] == {
            "group": "${{ github.workflow }}-${{ github.ref }}",
            "cancel-in-progress": True,
        }
    assert workflows["release.yml"]["concurrency"] == {
        "group": "release-${{ github.ref }}",
        "cancel-in-progress": False,
    }
    assert workflows["cloudflare-deploy.yml"]["jobs"]["deploy"]["concurrency"] == {
        "group": "cloudflare-${{ startsWith(github.ref, 'refs/tags/v') && 'production' || 'staging' }}",
        "cancel-in-progress": False,
    }


def test_workflows_use_separate_commands_and_release_write_isolation(
    render: Render,
) -> None:
    project = render("Default")
    workflows = load_workflows(project)
    check = (project / ".github" / "workflows" / "check.yml").read_text()
    test = (project / ".github" / "workflows" / "test.yml").read_text()
    build = (project / ".github" / "workflows" / "build.yml").read_text()
    release = workflows["release.yml"]
    prepare = release["jobs"]["prepare"]
    publish = release["jobs"]["publish"]
    publish_text = yaml.safe_dump(publish)

    assert "devbox run check" in check
    assert "devbox run test" not in check
    assert "devbox run build" not in check
    assert "devbox run test" in test
    assert "test-e2e:" not in test
    assert "devbox run build" in build
    assert prepare["permissions"] == {"contents": "read"}
    assert publish["permissions"] == {"contents": "write"}
    assert publish["needs"] == "prepare"
    assert [step["name"] for step in publish["steps"]] == [
        "Download release artifacts",
        "Publish GitHub Release",
    ]
    assert "actions/download-artifact@" in publish_text
    for forbidden in ("checkout", "Devbox", "devbox", "bun ", "uv ", "cargo "):
        assert forbidden not in publish_text
    assert (
        "GH_TOKEN: ${{ github.token }}"
        in (project / ".github" / "workflows" / "release.yml").read_text()
    )
    assert (
        'tags:\n      - "v*"'
        in (project / ".github" / "workflows" / "release.yml").read_text()
    )


def test_buildx_is_conditional_and_precedes_fastapi_builds(render: Render) -> None:
    fastapi = render(
        "FastAPI",
        {"components": ["backend"], "backend_variants": ["fastapi"]},
    )
    hono = render(
        "Hono",
        {"components": ["backend"], "backend_variants": ["hono"]},
    )
    composed = render(
        "Composed",
        {
            "frontend_variant": "astro",
            "components": ["frontend", "backend"],
            "backend_variants": ["fastapi"],
        },
    )

    for name in ("build.yml", "release.yml"):
        text = (fastapi / ".github" / "workflows" / name).read_text()
        assert text.index("Set up Docker Buildx") < text.index("devbox run build")
        assert (
            "docker/setup-buildx-action@e468171a9de216ec08956ac3ada2f0791b6bd435 # v3.11.1"
            in text
        )
        assert "--cache-from type=gha,scope=fastapi" in text
        assert "--cache-to type=gha,mode=max,scope=fastapi" in text
    cloudflare = (
        composed / ".github" / "workflows" / "cloudflare-deploy.yml"
    ).read_text()
    assert cloudflare.index("Set up Docker Buildx") < cloudflare.index(
        "devbox run build"
    )
    assert "DOCKER_CACHE_ARGS" in cloudflare
    assert "Set up Docker Buildx" not in "\n".join(
        path.read_text() for path in workflow_paths(hono)
    )


def test_download_caches_are_safe_and_conditionally_rendered(render: Render) -> None:
    everything = render(
        "EverythingCached",
        {
            "components": ["frontend", "client", "backend"],
            "backend_variants": ["hono", "fastapi"],
            "frontend_playwright": True,
            "client_playwright": True,
        },
    )
    fastapi = render(
        "FastAPIOnly",
        {"components": ["backend"], "backend_variants": ["fastapi"]},
    )
    default = render("DefaultCached")

    all_text = "\n".join(path.read_text() for path in workflow_paths(everything))
    allowed_paths = {
        "~/.bun/install/cache",
        "~/.cargo/registry",
        "~/.cargo/git",
        "~/.cache/uv",
        "~/.cache/ms-playwright",
    }
    rendered_paths: set[str] = set()
    for workflow in load_workflows(everything).values():
        for job in workflow["jobs"].values():
            for step in job["steps"]:
                if step.get("name", "").startswith("Cache "):
                    rendered_paths.update(step["with"]["path"].splitlines())
    assert rendered_paths == allowed_paths
    assert "node_modules" not in all_text
    assert ".venv" not in all_text
    assert ".terraform" not in all_text
    assert "target" not in "\n".join(rendered_paths)
    assert "1.62.1" in all_text
    fastapi_text = "\n".join(path.read_text() for path in workflow_paths(fastapi))
    assert "~/.cache/uv" in fastapi_text
    assert "~/.bun/install/cache" not in fastapi_text
    assert "~/.cargo" not in fastapi_text
    default_text = "\n".join(path.read_text() for path in workflow_paths(default))
    assert "~/.bun/install/cache" in default_text
    assert "~/.cache/uv" not in default_text
    assert "~/.cargo" not in default_text
    assert "~/.cache/ms-playwright" not in default_text


def test_playwright_installs_once_per_job_and_runs_both_suites(render: Render) -> None:
    project = render(
        "BothPlaywright",
        {
            "components": ["frontend", "client"],
            "frontend_playwright": True,
            "client_playwright": True,
        },
    )
    test = (project / ".github" / "workflows" / "test.yml").read_text()
    release = (project / ".github" / "workflows" / "release.yml").read_text()
    scripts = yaml.safe_load((project / "devbox.json").read_text())["shell"]["scripts"]

    assert test.count("playwright install --with-deps chromium") == 1
    assert release.count("playwright install --with-deps chromium") == 1
    assert scripts["test:e2e"] == [
        "bun run --cwd frontend test:e2e",
        "bun run --cwd client test:e2e",
    ]


def test_rendered_workflows_pass_actionlint(render: Render) -> None:
    project = render(
        "Linted",
        {
            "components": ["frontend", "client", "backend"],
            "backend_variants": ["hono", "fastapi"],
            "frontend_variant": "astro",
            "frontend_playwright": True,
            "client_playwright": True,
        },
    )
    result = subprocess.run(
        ["actionlint", *map(str, workflow_paths(project))],
        cwd=project,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_fastapi_workflows_omit_unselected_runtime_setup(render: Render) -> None:
    project = render(
        "FastAPIResidue",
        {"components": ["backend"], "backend_variants": ["fastapi"]},
    )
    all_text = "\n".join(path.read_text() for path in workflow_paths(project))

    assert "Tauri" not in all_text
    assert "playwright" not in all_text
    assert "frontend.tar.gz" not in all_text
    assert "hono-worker.tar.gz" not in all_text
    assert "fastapi-backend.tar" in all_text
