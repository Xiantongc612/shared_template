import hashlib
import importlib
import io
import json
import sys
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
integration = importlib.import_module("scripts.generated_integration")


def test_cases_cover_minimal_and_all_compatible_integrations() -> None:
    assert list(integration.CASES) == [
        "react",
        "react-integrations",
        "astro",
        "astro-integrations",
        "tauri",
        "tauri-integrations",
        "hono",
        "hono-integrations",
        "fastapi",
        "fastapi-integrations",
    ]
    assert [case.family for case in integration.CASE_LIST] == [
        "react",
        "react",
        "astro",
        "astro",
        "tauri",
        "tauri",
        "hono",
        "hono",
        "fastapi",
        "fastapi",
    ]
    assert integration.CASES["react-integrations"].answers == {
        "frontend_playwright": True,
        "frontend_ai_sdk": True,
        "frontend_tanstack_query": True,
        "frontend_i18next": True,
    }
    assert integration.CASES["astro-integrations"].answers == {
        "frontend_variant": "astro",
        "frontend_playwright": True,
        "frontend_ai_sdk": True,
        "frontend_i18next": True,
    }
    assert integration.CASES["tauri-integrations"].e2e_component == "client"
    assert integration.CASES["hono-integrations"].answers["hono_ai_sdk"] is True
    assert (
        integration.CASES["fastapi-integrations"].answers["fastapi_pydantic_ai"] is True
    )


def test_root_devbox_exposes_exact_focused_commands() -> None:
    root = Path(__file__).parents[1]
    scripts = json.loads((root / "devbox.json").read_text())["shell"]["scripts"]

    for case_name in integration.CASES:
        assert scripts[f"integration:{case_name}"] == [
            f"uv run --locked python scripts/generated_integration.py {case_name}"
        ]
    assert scripts["integration"] == [
        "uv run --locked python scripts/generated_integration.py all"
    ]


def write_static_dist(project: Path, script_reference: str = "assets/app.js") -> None:
    dist = project / "frontend" / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "assets" / "app.js").write_text("console.log('built')")
    (dist / "assets" / "app.css").write_text("body { color: black; }")
    (dist / "assets" / "logo.svg").write_text("<svg></svg>")
    (dist / "index.html").write_text(
        "<!doctype html><html><head>"
        '<link rel="stylesheet" href="/assets/app.css">'
        '<link rel="modulepreload" href="assets/app.js">'
        f'<script type="module" src="{script_reference}"></script>'
        "</head><body>Integration React"
        '<img src="assets/logo.svg"></body></html>'
    )


def test_static_validator_checks_document_marker_and_local_assets(
    tmp_path: Path,
) -> None:
    write_static_dist(tmp_path)

    integration.validate_static_dist(tmp_path, "Integration React")


@pytest.mark.parametrize(
    "reference", ["src/main.tsx", "../outside.js", "assets/missing.js"]
)
def test_static_validator_rejects_invalid_references(
    tmp_path: Path, reference: str
) -> None:
    write_static_dist(tmp_path, reference)

    with pytest.raises(RuntimeError):
        integration.validate_static_dist(tmp_path, "Integration React")


def test_hono_validator_imports_nonempty_worker_with_bun(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle = tmp_path / "backend" / "hono" / "dist" / "index.js"
    bundle.parent.mkdir(parents=True)
    bundle.write_text("export default { fetch() {} }")
    calls: list[list[str]] = []

    def fake_run(
        arguments: integration.Sequence[str],
        cwd: Path,
        environment: integration.Mapping[str, str],
    ) -> None:
        calls.append(list(arguments))

    monkeypatch.setattr(integration, "run", fake_run)

    integration.validate_hono_bundle(tmp_path, {})

    assert calls[0][0:2] == ["bun", "--eval"]
    assert calls[0][-1] == bundle.resolve().as_uri()
    assert "/health" in calls[0][2]


def test_hono_validator_rejects_empty_bundle(tmp_path: Path) -> None:
    bundle = tmp_path / "backend" / "hono" / "dist" / "index.js"
    bundle.parent.mkdir(parents=True)
    bundle.touch()

    with pytest.raises(RuntimeError, match="empty Hono bundle"):
        integration.validate_hono_bundle(tmp_path)


def test_tauri_validator_checks_packages_without_launching_gui(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle = tmp_path / "client" / "src-tauri" / "target" / "release" / "bundle"
    deb = bundle / "deb" / "app.deb"
    appimage = bundle / "appimage" / "app.AppImage"
    deb.parent.mkdir(parents=True)
    appimage.parent.mkdir(parents=True)
    deb.write_bytes(b"deb")
    appimage.write_bytes(b"appimage")
    appimage.chmod(0o755)

    def fake_subprocess_run(arguments: list[str], **kwargs: object) -> SimpleNamespace:
        if "--field" in arguments:
            return SimpleNamespace(stdout="app\n0.1.0\namd64\n")
        return SimpleNamespace(stdout="-rwxr-xr-x root/root ./usr/bin/app\n")

    def fake_extract(
        arguments: integration.Sequence[str],
        cwd: Path,
        environment: integration.Mapping[str, str],
    ) -> None:
        root = cwd / "squashfs-root"
        executable = root / "usr" / "bin" / "app"
        executable.parent.mkdir(parents=True)
        (root / "AppRun").write_text("#!/bin/sh\n")
        (root / "AppRun").chmod(0o755)
        (root / "app.desktop").write_text("[Desktop Entry]\nName=App\n")
        executable.write_bytes(b"\x7fELFpayload")
        executable.chmod(0o755)

    monkeypatch.setattr(integration.subprocess, "run", fake_subprocess_run)
    monkeypatch.setattr(integration, "run", fake_extract)

    integration.validate_tauri_bundles(tmp_path, {})


def test_tauri_validator_rejects_nonexecutable_appimage(tmp_path: Path) -> None:
    bundle = tmp_path / "client" / "src-tauri" / "target" / "release" / "bundle"
    deb = bundle / "deb" / "app.deb"
    appimage = bundle / "appimage" / "app.AppImage"
    deb.parent.mkdir(parents=True)
    appimage.parent.mkdir(parents=True)
    deb.write_bytes(b"deb")
    appimage.write_bytes(b"appimage")
    appimage.chmod(0o644)

    with pytest.raises(RuntimeError, match="not executable"):
        integration.validate_tauri_bundles(tmp_path, {})


def descriptor(data: bytes) -> dict[str, object]:
    return {
        "mediaType": "application/vnd.oci.image.manifest.v1+json",
        "digest": f"sha256:{hashlib.sha256(data).hexdigest()}",
        "size": len(data),
    }


def write_oci_archive(project: Path, corrupt_layer_size: bool = False) -> None:
    command = [
        "/app/.venv/bin/uvicorn",
        "app.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
    ]
    config = json.dumps({"config": {"Cmd": command}}).encode()
    layer = b"layer payload"
    config_descriptor = descriptor(config)
    layer_descriptor = descriptor(layer)
    layer_descriptor["mediaType"] = "application/vnd.oci.image.layer.v1.tar+gzip"
    if corrupt_layer_size:
        layer_descriptor["size"] = len(layer) + 1
    manifest = json.dumps(
        {
            "schemaVersion": 2,
            "config": config_descriptor,
            "layers": [layer_descriptor],
        }
    ).encode()
    index = json.dumps(
        {"schemaVersion": 2, "manifests": [descriptor(manifest)]}
    ).encode()
    files = {
        "oci-layout": json.dumps({"imageLayoutVersion": "1.0.0"}).encode(),
        "index.json": index,
        f"blobs/sha256/{hashlib.sha256(config).hexdigest()}": config,
        f"blobs/sha256/{hashlib.sha256(layer).hexdigest()}": layer,
        f"blobs/sha256/{hashlib.sha256(manifest).hexdigest()}": manifest,
    }
    archive = project / "backend" / "fastapi" / "dist" / "fastapi-backend.tar"
    archive.parent.mkdir(parents=True)
    with tarfile.open(archive, "w") as output:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            output.addfile(info, io.BytesIO(data))


def test_fastapi_validator_checks_complete_oci_graph_and_command(
    tmp_path: Path,
) -> None:
    write_oci_archive(tmp_path)

    integration.validate_fastapi_oci(tmp_path)


def test_fastapi_validator_rejects_malformed_descriptor(tmp_path: Path) -> None:
    write_oci_archive(tmp_path, corrupt_layer_size=True)

    with pytest.raises(RuntimeError, match="size mismatch"):
        integration.validate_fastapi_oci(tmp_path)


def test_artifact_dispatch_uses_component_family(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[Path, str]] = []
    monkeypatch.setattr(
        integration,
        "validate_static_dist",
        lambda project, marker: calls.append((project, marker)),
    )

    integration.assert_artifacts(integration.CASES["react-integrations"], tmp_path)

    assert calls == [(tmp_path, "Integration React-Integrations")]
