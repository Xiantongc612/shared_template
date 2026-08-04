from support import Render


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


def test_all_component_workflows_are_conditional_and_linux_only(
    render: Render,
) -> None:
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
