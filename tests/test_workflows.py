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
        ("auto-merge.yml", "auto-merge"): 10,
        ("validate.yml", "check"): 60,
        ("validate.yml", "test"): 60,
        ("validate.yml", "test-e2e"): 60,
        ("release.yml", "build"): 120,
        ("release.yml", "publish"): 10,
        ("deploy.yml", "deploy"): 60,
    }

    assert workflows.keys() == {
        "auto-merge.yml",
        "deploy.yml",
        "release.yml",
        "validate.yml",
    }
    for workflow_name, workflow in workflows.items():
        assert isinstance(workflow, dict)
        for job_name, job in workflow["jobs"].items():
            assert job["runs-on"] == "ubuntu-24.04"
            assert (
                job["timeout-minutes"] == expected_timeouts[(workflow_name, job_name)]
            )

    assert workflows["validate.yml"]["concurrency"] == {
        "group": "${{ github.workflow }}-${{ github.ref }}",
        "cancel-in-progress": True,
    }
    assert workflows["release.yml"]["concurrency"] == {
        "group": "release-${{ github.event.workflow_run.head_branch == 'main' && 'staging' || 'production' }}",
        "cancel-in-progress": False,
    }
    assert workflows["deploy.yml"]["jobs"]["deploy"]["concurrency"] == {
        "group": "cloudflare-${{ github.event.workflow_run.head_branch == 'main' && 'staging' || 'production' }}",
        "cancel-in-progress": False,
    }


def test_pipeline_workflows_chain_by_workflow_run(render: Render) -> None:
    project = render(
        "Pipeline",
        {"components": ["backend"], "backend_variants": ["hono"]},
    )
    workflows = load_workflows(project)

    assert workflows["validate.yml"][True] == {
        "pull_request": None,
        "push": {"branches": ["main"], "tags": ["v*"]},
    }
    assert workflows["release.yml"][True]["workflow_run"] == {
        "workflows": ["Validate"],
        "types": ["completed"],
    }
    assert workflows["deploy.yml"][True]["workflow_run"] == {
        "workflows": ["Release"],
        "types": ["completed"],
    }
    release_build = workflows["release.yml"]["jobs"]["build"]
    deploy = workflows["deploy.yml"]["jobs"]["deploy"]
    for job in (release_build, deploy):
        assert job["if"] == (
            "github.event.workflow_run.conclusion == 'success' && "
            "github.event.workflow_run.event != 'pull_request'"
        )

    release_checkout = release_build["steps"][0]
    assert (
        release_checkout["with"]["ref"] == "${{ github.event.workflow_run.head_sha }}"
    )
    deploy_checkout = deploy["steps"][0]
    assert deploy_checkout["with"]["ref"] == "${{ github.event.workflow_run.head_sha }}"

    assert deploy["environment"] == (
        "${{ github.event.workflow_run.head_branch == 'main' && 'staging' || 'production' }}"
    )
    assert deploy["env"]["DEPLOYMENT_ENV"] == (
        "${{ github.event.workflow_run.head_branch == 'main' && 'staging' || 'production' }}"
    )
    assert deploy["env"]["GITHUB_SHA"] == "${{ github.event.workflow_run.head_sha }}"


def test_pipeline_publish_is_production_only_and_consumes_release_artifacts(
    render: Render,
) -> None:
    project = render(
        "Publish", {"components": ["backend"], "backend_variants": ["hono"]}
    )
    workflows = load_workflows(project)
    release = workflows["release.yml"]
    build = release["jobs"]["build"]
    publish = release["jobs"]["publish"]
    publish_text = yaml.safe_dump(publish)

    assert build["if"] == (
        "github.event.workflow_run.conclusion == 'success' && "
        "github.event.workflow_run.event != 'pull_request'"
    )
    assert publish["needs"] == "build"
    assert publish["if"] == "startsWith(github.event.workflow_run.head_branch, 'v')"
    assert publish["environment"] == "production"
    assert publish["permissions"] == {"contents": "write"}
    assert [step["name"] for step in publish["steps"]] == [
        "Download release artifacts",
        "Publish GitHub Release",
    ]
    assert "actions/download-artifact@" in publish_text
    for forbidden in ("checkout", "Devbox", "devbox", "bun ", "uv ", "cargo "):
        assert forbidden not in publish_text
    assert (
        'gh release create "${{ github.event.workflow_run.head_branch }}" --generate-notes'
        in (project / ".github" / "workflows" / "release.yml").read_text()
    )

    build_steps = {step["name"]: step for step in build["steps"]}
    assert "Build project artifacts" in build_steps
    assert "devbox run build" in build_steps["Build project artifacts"]["run"]
    assert "Upload Hono deploy artifact" in build_steps
    assert "Upload release artifacts" in build_steps


def test_pipeline_validate_never_builds_and_deploy_never_rebuilds(
    render: Render,
) -> None:
    project = render(
        "ConsumeArtifacts",
        {
            "components": ["backend"],
            "backend_variants": ["hono"],
            "frontend_variant": "astro",
        },
    )
    workflows = load_workflows(project)
    validate = (project / ".github" / "workflows" / "validate.yml").read_text()
    deploy = (project / ".github" / "workflows" / "deploy.yml").read_text()
    deploy_data = workflows["deploy.yml"]
    deploy_steps = {
        step["name"]: step for step in deploy_data["jobs"]["deploy"]["steps"]
    }

    assert "devbox run check" in validate
    assert "devbox run test" in validate
    assert "devbox run build" not in validate
    assert "devbox run build" not in deploy
    assert "Download Hono deploy artifact" in deploy_steps
    assert deploy_steps["Download Hono deploy artifact"]["with"] == {
        "name": "hono-dist",
        "path": "backend/hono",
    }
    assert "Release Hono Worker" in deploy_steps
    assert deploy_steps["Release Hono Worker"]["run"] == (
        'bun run --cwd backend/hono release:"$DEPLOYMENT_ENV"'
    )


def test_workflows_use_separate_commands_and_release_write_isolation(
    render: Render,
) -> None:
    project = render("Default")
    workflows = load_workflows(project)
    validate = (project / ".github" / "workflows" / "validate.yml").read_text()
    release = workflows["release.yml"]
    publish = release["jobs"]["publish"]
    publish_text = yaml.safe_dump(publish)

    assert "devbox run check" in validate
    assert "devbox run test" in validate
    assert "devbox run build" not in validate
    assert release["permissions"] == {"contents": "read"}
    assert publish["permissions"] == {"contents": "write"}
    assert publish["needs"] == "build"
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

    release = (fastapi / ".github" / "workflows" / "release.yml").read_text()
    assert release.index("Set up Docker Buildx") < release.index("devbox run build")
    assert (
        "docker/setup-buildx-action@e468171a9de216ec08956ac3ada2f0791b6bd435 # v3.11.1"
        in release
    )
    assert "--cache-from type=gha,scope=fastapi" in release
    assert "--cache-to type=gha,mode=max,scope=fastapi" in release
    deploy = (composed / ".github" / "workflows" / "deploy.yml").read_text()
    assert "Set up Docker Buildx" not in deploy
    assert "DOCKER_CACHE_ARGS" not in deploy
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
    validate = (project / ".github" / "workflows" / "validate.yml").read_text()
    release = (project / ".github" / "workflows" / "release.yml").read_text()
    scripts = yaml.safe_load((project / "devbox.json").read_text())["shell"]["scripts"]

    assert validate.count("playwright install --with-deps chromium") == 1
    assert "playwright" not in release
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


def test_rendered_cache_steps_have_prefix_restore_keys(render: Render) -> None:
    project = render(
        "RestoreKeys",
        {
            "components": ["frontend", "client", "backend"],
            "backend_variants": ["hono", "fastapi"],
            "frontend_playwright": True,
            "client_playwright": True,
        },
    )

    for workflow in load_workflows(project).values():
        for job in workflow["jobs"].values():
            for step in job["steps"]:
                if not step.get("name", "").startswith("Cache "):
                    continue
                with_ = step["with"]
                assert "restore-keys" in with_
                assert with_["restore-keys"].endswith("-")
                assert with_["key"].startswith(with_["restore-keys"])


def test_cache_downloads_toggle_removes_download_store_caches(render: Render) -> None:
    project = render(
        "CacheDownloadsOff",
        {
            "components": ["frontend", "client", "backend"],
            "backend_variants": ["hono", "fastapi"],
            "frontend_playwright": True,
            "client_playwright": True,
            "cache_downloads": False,
        },
    )
    workflow_text = "\n".join(path.read_text() for path in workflow_paths(project))

    assert "actions/cache@" not in workflow_text
    assert "restore-keys" not in workflow_text
    assert "enable-cache: true" in workflow_text


def test_cache_nix_toggle_disables_devbox_nix_store_cache(render: Render) -> None:
    off = render("NixCacheOff", {"components": ["frontend"], "cache_nix": False})
    off_text = "\n".join(path.read_text() for path in workflow_paths(off))

    assert "enable-cache: false" in off_text
    assert "enable-cache: true" not in off_text

    on = render("NixCacheOn", {"components": ["frontend"]})
    on_text = "\n".join(path.read_text() for path in workflow_paths(on))

    assert "enable-cache: true" in on_text
    assert "enable-cache: false" not in on_text


def test_cache_docker_toggle_gates_fastapi_build_cache(render: Render) -> None:
    off = render(
        "DockerCacheOff",
        {
            "components": ["backend"],
            "backend_variants": ["fastapi"],
            "cache_docker": False,
        },
    )
    off_release = (off / ".github" / "workflows" / "release.yml").read_text()

    assert "DOCKER_CACHE_ARGS" in off_release
    assert "DOCKER_CACHE_ARGS: --cache-from" not in off_release
    assert "--cache-to type=gha" not in off_release
    assert "Set up Docker Buildx" in off_release

    on = render(
        "DockerCacheOn",
        {"components": ["backend"], "backend_variants": ["fastapi"]},
    )
    on_release = (on / ".github" / "workflows" / "release.yml").read_text()

    assert "--cache-from type=gha,scope=fastapi" in on_release
    assert "--cache-to type=gha,mode=max,scope=fastapi" in on_release


def test_repository_validate_workflow_caches_uv_and_scopes_concurrency() -> None:
    validate = yaml.safe_load(
        (ROOT / ".github" / "workflows" / "validate.yml").read_text()
    )
    steps = {step["name"]: step for step in validate["jobs"]["check"]["steps"]}
    cache = steps["Cache uv downloads"]

    assert cache["with"]["path"] == "~/.cache/uv"
    assert cache["with"]["restore-keys"].endswith("-")
    assert cache["with"]["key"].startswith(cache["with"]["restore-keys"])
    assert validate["concurrency"] == {
        "group": "${{ github.workflow }}-${{ github.ref }}",
        "cancel-in-progress": True,
    }


def test_repository_workflows_scope_concurrency() -> None:
    for path in (ROOT / ".github" / "workflows").iterdir():
        workflow = yaml.safe_load(path.read_text())
        assert "concurrency" in workflow
        assert workflow["concurrency"]["group"]
