import json

from support import Render

TAURI_ICONS = [
    "icons/32x32.png",
    "icons/128x128.png",
    "icons/128x128@2x.png",
    "icons/icon.icns",
    "icons/icon.ico",
]
TAURI_ICON_INIT_COMMAND = (
    "test -f client/src-tauri/icons/32x32.png && "
    "test -f client/src-tauri/icons/128x128.png && "
    "test -f client/src-tauri/icons/128x128@2x.png && "
    "test -f client/src-tauri/icons/icon.icns && "
    "test -f client/src-tauri/icons/icon.ico || "
    "bun run --cwd client tauri icon src-tauri/app-icon.svg"
)


def test_generated_agents_only_describes_selected_components(render: Render) -> None:
    project = render(
        "FastAPI",
        {"components": ["backend"], "backend_variants": ["fastapi"]},
    )
    instructions = (project / "AGENTS.md").read_text()

    assert "FastAPI Backend" in instructions
    assert "React Frontend" not in instructions
    assert "Astro Frontend" not in instructions
    assert "Tauri Client" not in instructions
    assert "Hono Backend" not in instructions


def test_react_integrations_are_independently_rendered(render: Render) -> None:
    project = render(
        "ReactAI",
        {"frontend_ai_sdk": True},
    )
    package = json.loads((project / "frontend" / "package.json").read_text())

    assert "ai" in package["dependencies"]
    assert "@tanstack/react-query" not in package["dependencies"]
    assert "i18next" not in package["dependencies"]
    assert "@playwright/test" not in package["devDependencies"]
    assert (project / "frontend" / "src" / "integrations" / "ai.ts").is_file()
    assert not (project / "frontend" / "playwright.config.ts").exists()


def test_react_all_integrations_render_configuration(render: Render) -> None:
    project = render(
        "ReactAll",
        {
            "frontend_playwright": True,
            "frontend_ai_sdk": True,
            "frontend_tanstack_query": True,
            "frontend_i18next": True,
        },
    )
    frontend = project / "frontend"
    package = json.loads((frontend / "package.json").read_text())

    assert {
        "ai",
        "zod",
        "@tanstack/react-query",
        "i18next",
        "react-i18next",
    } <= package["dependencies"].keys()
    assert "@playwright/test" in package["devDependencies"]
    assert (frontend / "playwright.config.ts").is_file()
    assert (frontend / "e2e" / "app.spec.ts").is_file()
    assert (frontend / "src" / "integrations" / "ai.ts").is_file()
    assert (frontend / "src" / "integrations" / "i18n.ts").is_file()
    assert "QueryClientProvider" in (frontend / "src" / "main.tsx").read_text()


def test_react_files_are_absent_without_react_variant(render: Render) -> None:
    client = render("ClientOnly", {"components": ["client"]})
    astro = render("AstroOnly", {"frontend_variant": "astro"})

    assert not (client / "frontend").exists()
    assert not (astro / "frontend" / "src" / "App.tsx").exists()


def test_astro_generator_is_independent(render: Render) -> None:
    project = render(
        "AstroAll",
        {
            "frontend_variant": "astro",
            "frontend_playwright": True,
            "frontend_ai_sdk": True,
            "frontend_i18next": True,
        },
    )
    frontend = project / "frontend"
    package = json.loads((frontend / "package.json").read_text())

    assert "astro" in package["dependencies"]
    assert "ai" in package["dependencies"]
    assert "i18next" in package["dependencies"]
    assert "react" not in package["dependencies"]
    assert "@tanstack/react-query" not in package["dependencies"]
    biome = json.loads((frontend / "biome.json").read_text())
    assert biome["overrides"][0]["includes"] == ["**/*.astro"]
    assert biome["overrides"][0]["linter"]["enabled"] is False
    assert (frontend / "src" / "pages" / "index.astro").is_file()
    assert not (frontend / "src" / "App.tsx").exists()
    assert (frontend / "playwright.config.ts").is_file()


def test_client_generator_is_independent(render: Render) -> None:
    project = render(
        "ClientAll",
        {
            "components": ["client"],
            "client_playwright": True,
            "client_ai_sdk": True,
            "client_tanstack_query": True,
            "client_i18next": True,
        },
    )
    client = project / "client"
    package = json.loads((client / "package.json").read_text())

    assert "@tauri-apps/api" in package["dependencies"]
    assert "ai" in package["dependencies"]
    assert "@tanstack/react-query" in package["dependencies"]
    assert "i18next" in package["dependencies"]
    devbox = json.loads((project / "devbox.json").read_text())
    icon_commands = [
        command
        for command in devbox["shell"]["scripts"]["init"]
        if "tauri icon" in command
    ]
    assert icon_commands == [TAURI_ICON_INIT_COMMAND]
    assert "icon.png" not in icon_commands[0]
    assert (client / "src-tauri" / "app-icon.svg").is_file()
    tauri_config = json.loads((client / "src-tauri" / "tauri.conf.json").read_text())
    assert tauri_config["bundle"]["icon"] == TAURI_ICONS
    assert (client / "src-tauri" / "src" / "lib.rs").is_file()
    assert not (project / "frontend").exists()


def test_client_devbox_exposes_host_ldd_for_appimage_bundling(
    render: Render,
) -> None:
    project = render("ClientLdd", {"components": ["client"]})
    devbox = json.loads((project / "devbox.json").read_text())
    init_hook = devbox["shell"]["init_hook"]

    assert len(init_hook) == 1
    assert "/usr/bin/ldd" in init_hook[0]
    assert 'export PATH="$PWD/.devbox-host-bin:$PATH"' in init_hook[0]

    frontend = render("FrontendNoLdd", {"components": ["frontend"]})
    frontend_devbox = json.loads((frontend / "devbox.json").read_text())
    assert frontend_devbox["shell"]["init_hook"] == []


def test_hono_generator_and_optional_ai(render: Render) -> None:
    project = render(
        "HonoAI",
        {
            "components": ["backend"],
            "backend_variants": ["hono"],
            "hono_ai_sdk": True,
        },
    )
    service = project / "backend" / "hono"
    package = json.loads((service / "package.json").read_text())

    assert "hono" in package["dependencies"]
    assert "ai" in package["dependencies"]
    assert (service / "wrangler.jsonc").is_file()
    assert (service / "src" / "ai.ts").is_file()
    assert not (project / "backend" / "fastapi").exists()


def test_fastapi_generator_and_optional_ai(render: Render) -> None:
    project = render(
        "FastAPIAI",
        {
            "components": ["backend"],
            "backend_variants": ["fastapi"],
            "fastapi_pydantic_ai": True,
        },
    )
    service = project / "backend" / "fastapi"
    pyproject = (service / "pyproject.toml").read_text()

    assert '"fastapi==' in pyproject
    assert '"pydantic-ai==' in pyproject
    assert (service / "Dockerfile").is_file()
    assert (service / "app" / "ai.py").is_file()
    assert not (project / "backend" / "hono").exists()


def test_all_components_have_independent_boundaries(render: Render) -> None:
    project = render(
        "FullStack",
        {
            "components": ["frontend", "client", "backend"],
            "backend_variants": ["hono", "fastapi"],
        },
    )

    assert (project / "frontend" / "package.json").is_file()
    assert (project / "client" / "package.json").is_file()
    assert (project / "client" / "src-tauri" / "Cargo.toml").is_file()
    assert (project / "backend" / "hono" / "package.json").is_file()
    assert (project / "backend" / "fastapi" / "pyproject.toml").is_file()
    assert not (project / "docker-compose.yml").exists()
    assert not (project / "packages").exists()


def test_both_backends_do_not_share_manifests(render: Render) -> None:
    project = render(
        "Backends",
        {
            "components": ["backend"],
            "backend_variants": ["hono", "fastapi"],
        },
    )

    assert (project / "backend" / "hono" / "package.json").is_file()
    assert not (project / "backend" / "hono" / "pyproject.toml").exists()
    assert (project / "backend" / "fastapi" / "pyproject.toml").is_file()
    assert not (project / "backend" / "fastapi" / "package.json").exists()


def test_unselected_runtimes_leave_no_residue(render: Render) -> None:
    project = render(
        "FastAPIOnly",
        {"components": ["backend"], "backend_variants": ["fastapi"]},
    )
    devbox = (project / "devbox.json").read_text()
    gitignore = (project / ".gitignore").read_text()
    all_text = "\n".join(
        path.read_text() for path in project.iterdir() if path.is_file()
    )

    assert "python@" in devbox
    assert "uv@" in devbox
    assert "bun" not in all_text
    assert "cargo" not in all_text
    assert "rustc" not in all_text
    assert "node_modules" not in gitignore
    assert ".venv/" in gitignore
