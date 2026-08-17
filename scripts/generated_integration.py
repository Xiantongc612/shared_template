import argparse
import hashlib
import json
import os
import stat
import subprocess
import tarfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from shutil import copy2, copytree
from tempfile import TemporaryDirectory
from typing import Any, Literal
from urllib.parse import unquote, urlsplit

from copier import run_copy

ROOT = Path(__file__).parents[1]
ComponentFamily = Literal[
    "react", "astro", "tauri", "hono", "fastapi", "scripts", "kmp"
]


@dataclass(frozen=True)
class IntegrationCase:
    name: str
    family: ComponentFamily
    answers: Mapping[str, Any] = field(default_factory=dict)
    e2e_component: Literal["frontend", "client"] | None = None


CASE_LIST = (
    IntegrationCase("react", "react"),
    IntegrationCase(
        "react-integrations",
        "react",
        {
            "frontend_playwright": True,
            "frontend_ai_sdk": True,
            "frontend_tanstack_query": True,
            "frontend_i18next": True,
        },
        "frontend",
    ),
    IntegrationCase("astro", "astro", {"frontend_variant": "astro"}),
    IntegrationCase(
        "astro-integrations",
        "astro",
        {
            "frontend_variant": "astro",
            "frontend_playwright": True,
            "frontend_ai_sdk": True,
            "frontend_i18next": True,
        },
        "frontend",
    ),
    IntegrationCase("tauri", "tauri", {"components": ["client"]}),
    IntegrationCase(
        "tauri-integrations",
        "tauri",
        {
            "components": ["client"],
            "client_playwright": True,
            "client_ai_sdk": True,
            "client_tanstack_query": True,
            "client_i18next": True,
        },
        "client",
    ),
    IntegrationCase(
        "hono", "hono", {"components": ["backend"], "backend_variants": ["hono"]}
    ),
    IntegrationCase(
        "hono-integrations",
        "hono",
        {
            "components": ["backend"],
            "backend_variants": ["hono"],
            "hono_ai_sdk": True,
        },
    ),
    IntegrationCase(
        "fastapi",
        "fastapi",
        {"components": ["backend"], "backend_variants": ["fastapi"]},
    ),
    IntegrationCase(
        "fastapi-integrations",
        "fastapi",
        {
            "components": ["backend"],
            "backend_variants": ["fastapi"],
            "fastapi_pydantic_ai": True,
        },
    ),
    IntegrationCase("scripts", "scripts", {"components": ["scripts"]}),
    IntegrationCase(
        "scripts-integrations",
        "scripts",
        {
            "components": ["scripts"],
            "python_data_analysis": True,
            "python_duckdb": True,
        },
    ),
    IntegrationCase("kmp", "kmp", {"components": ["kmp"]}),
)
CASES = {case.name: case for case in CASE_LIST}

CASE_GROUPS: dict[str, tuple[IntegrationCase, ...]] = {
    "tauri-all": (CASES["tauri"], CASES["tauri-integrations"]),
}


def run(arguments: Sequence[str], cwd: Path, environment: Mapping[str, str]) -> None:
    subprocess.run(arguments, cwd=cwd, env=environment, check=True)


class StaticIndexParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: set[str] = set()
        self.references: list[str] = []
        self.text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.add(tag)
        values = dict(attrs)
        src = values.get("src")
        href = values.get("href")
        srcset = values.get("srcset")
        if tag == "script" and src:
            self.references.append(src)
        if (
            tag == "link"
            and values.get("rel") in {"stylesheet", "modulepreload"}
            and href
        ):
            self.references.append(href)
        if tag == "img":
            if src:
                self.references.append(src)
            if srcset:
                self.references.extend(
                    candidate.strip().split(maxsplit=1)[0]
                    for candidate in srcset.split(",")
                    if candidate.strip()
                )

    def handle_data(self, data: str) -> None:
        self.text.append(data)


def validate_static_dist(project: Path, marker: str) -> None:
    dist = project / "frontend" / "dist"
    index = dist / "index.html"
    if not index.is_file() or index.stat().st_size == 0:
        raise RuntimeError(f"Missing or empty static index: {index}")

    parser = StaticIndexParser()
    try:
        parser.feed(index.read_text(encoding="utf-8"))
        parser.close()
    except (UnicodeDecodeError, ValueError) as error:
        raise RuntimeError(f"Invalid static index: {index}") from error
    if not {"html", "head", "body"}.issubset(parser.tags):
        raise RuntimeError(f"Static index lacks an HTML document structure: {index}")
    if marker not in "".join(parser.text):
        raise RuntimeError(f"Static index lacks expected marker {marker!r}: {index}")

    resolved_dist = dist.resolve()
    for reference in parser.references:
        parsed = urlsplit(reference)
        if parsed.scheme or parsed.netloc or reference.startswith("//"):
            continue
        path = unquote(parsed.path)
        if not path:
            continue
        source_path = PurePosixPath(path)
        if "src" in source_path.parts or source_path.suffix in {
            ".astro",
            ".jsx",
            ".tsx",
            ".ts",
        }:
            raise RuntimeError(f"Static index references source file: {reference}")
        artifact = (dist / path.lstrip("/")).resolve()
        try:
            artifact.relative_to(resolved_dist)
        except ValueError as error:
            raise RuntimeError(f"Static reference escapes dist: {reference}") from error
        if not artifact.is_file() or artifact.stat().st_size == 0:
            raise RuntimeError(f"Missing or empty static reference: {reference}")


def validate_hono_bundle(
    project: Path, environment: Mapping[str, str] | None = None
) -> None:
    bundle = project / "backend" / "hono" / "dist" / "index.js"
    if not bundle.is_file() or bundle.stat().st_size == 0:
        raise RuntimeError(f"Missing or empty Hono bundle: {bundle}")
    script = """
const worker = (await import(process.argv[1])).default;
if (!worker || typeof worker.fetch !== "function") throw new Error("missing fetch handler");
const response = await worker.fetch(new Request("https://integration.invalid/health"), {}, {});
const body = await response.json();
if (response.status !== 200 || body.status !== "ok" || Object.keys(body).length !== 1) {
  throw new Error(`unexpected health response: ${response.status} ${JSON.stringify(body)}`);
}
""".strip()
    run(
        ["bun", "--eval", script, bundle.resolve().as_uri()],
        project,
        environment or os.environ.copy(),
    )


def _is_native_executable(item: Path, app_run: Path) -> bool:
    if not item.is_file() or not os.access(item, os.X_OK) or item == app_run:
        return False
    with item.open("rb") as contents:
        return contents.read(4) == b"\x7fELF"


def validate_tauri_bundles(
    project: Path, environment: Mapping[str, str] | None = None
) -> None:
    command_environment = environment or os.environ.copy()
    cargo_target = command_environment.get("CARGO_TARGET_DIR")
    if cargo_target:
        target = Path(cargo_target)
    else:
        target = project / "client" / "src-tauri" / "target"
    bundle = target / "release" / "bundle"
    debs = list((bundle / "deb").glob("*.deb"))
    appimages = list((bundle / "appimage").glob("*.AppImage"))
    if not debs or any(artifact.stat().st_size == 0 for artifact in debs):
        raise RuntimeError("Missing or empty Tauri Debian bundle")
    if not appimages or any(artifact.stat().st_size == 0 for artifact in appimages):
        raise RuntimeError("Missing or empty Tauri AppImage bundle")
    for appimage in appimages:
        if not appimage.stat().st_mode & stat.S_IXUSR:
            raise RuntimeError(f"AppImage is not executable: {appimage}")

    for deb in debs:
        metadata = subprocess.run(
            ["dpkg-deb", "--field", str(deb), "Package", "Version", "Architecture"],
            cwd=project,
            env=command_environment,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        payload = subprocess.run(
            ["dpkg-deb", "--contents", str(deb)],
            cwd=project,
            env=command_environment,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        if len(metadata.splitlines()) < 3:
            raise RuntimeError(f"Incomplete Debian metadata: {deb}")
        if not any(line.startswith("-rwx") for line in payload.splitlines()):
            raise RuntimeError(f"Debian bundle lacks an executable payload: {deb}")

    for appimage in appimages:
        with TemporaryDirectory(prefix="tauri-appimage-") as temporary:
            extraction = Path(temporary)
            run(
                [str(appimage.resolve()), "--appimage-extract"],
                extraction,
                command_environment,
            )
            root = extraction / "squashfs-root"
            app_run = root / "AppRun"
            desktops = list(root.glob("*.desktop"))
            if not app_run.is_file() or not os.access(app_run, os.X_OK):
                raise RuntimeError(f"AppImage lacks executable AppRun: {appimage}")
            if not desktops or any(item.stat().st_size == 0 for item in desktops):
                raise RuntimeError(f"AppImage lacks desktop metadata: {appimage}")

            native_payloads = [
                item for item in root.rglob("*") if _is_native_executable(item, app_run)
            ]
            if not native_payloads:
                raise RuntimeError(
                    f"AppImage lacks a native executable payload: {appimage}"
                )


def _read_oci_archive(archive: Path) -> dict[str, bytes]:
    if not archive.is_file() or archive.stat().st_size == 0:
        raise RuntimeError(f"Missing or empty OCI archive: {archive}")
    files: dict[str, bytes] = {}
    with tarfile.open(archive) as contents:
        for member in contents.getmembers():
            if member.isfile():
                extracted = contents.extractfile(member)
                if extracted is not None:
                    files[member.name.removeprefix("./")] = extracted.read()
    return files


def _parse_json(data: bytes, description: str) -> dict[str, Any]:
    try:
        value = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Invalid JSON in {description}") from error
    if not isinstance(value, dict):
        raise TypeError(f"Expected a JSON object in {description}")
    return value


def validate_fastapi_oci(project: Path) -> None:
    archive = project / "backend" / "fastapi" / "dist" / "fastapi-backend.tar"
    files = _read_oci_archive(archive)
    if "oci-layout" not in files or "index.json" not in files:
        raise RuntimeError(f"OCI archive lacks top-level layout files: {archive}")
    layout = _parse_json(files["oci-layout"], "oci-layout")
    if layout.get("imageLayoutVersion") != "1.0.0":
        raise RuntimeError("Unsupported OCI image layout version")
    index = _parse_json(files["index.json"], "index.json")
    manifests: list[dict[str, Any]] = []

    def read_descriptor(descriptor: Any) -> dict[str, Any]:
        if not isinstance(descriptor, dict):
            raise TypeError("Invalid OCI descriptor")
        digest = descriptor.get("digest")
        size = descriptor.get("size")
        if not isinstance(digest, str) or not digest.startswith("sha256:"):
            raise RuntimeError("OCI descriptor lacks a sha256 digest")
        path = f"blobs/sha256/{digest.removeprefix('sha256:')}"
        data = files.get(path)
        if data is None:
            raise RuntimeError(f"Missing OCI descriptor blob: {digest}")
        if not isinstance(size, int) or size != len(data):
            raise RuntimeError(f"OCI descriptor size mismatch: {digest}")
        if hashlib.sha256(data).hexdigest() != digest.removeprefix("sha256:"):
            raise RuntimeError(f"OCI descriptor digest mismatch: {digest}")
        return _parse_json(data, digest)

    def visit(descriptor: Any) -> None:
        document = read_descriptor(descriptor)
        if "manifests" in document:
            child_descriptors = document["manifests"]
            if not isinstance(child_descriptors, list) or not child_descriptors:
                raise RuntimeError("OCI image index has no manifests")
            for child in child_descriptors:
                visit(child)
            return
        config_descriptor = document.get("config")
        layers = document.get("layers")
        if (
            not isinstance(config_descriptor, dict)
            or not isinstance(layers, list)
            or not layers
        ):
            raise RuntimeError("Invalid OCI image manifest")
        config = read_descriptor(config_descriptor)
        for layer in layers:
            read_descriptor_bytes(layer)
        annotations = descriptor.get("annotations", {})
        is_attestation = (
            isinstance(annotations, dict)
            and annotations.get("vnd.docker.reference.type") == "attestation-manifest"
        )
        if not is_attestation:
            manifests.append(config)

    def read_descriptor_bytes(descriptor: Any) -> None:
        if not isinstance(descriptor, dict):
            raise TypeError("Invalid OCI layer descriptor")
        digest = descriptor.get("digest")
        size = descriptor.get("size")
        if not isinstance(digest, str) or not digest.startswith("sha256:"):
            raise RuntimeError("OCI layer lacks a sha256 digest")
        data = files.get(f"blobs/sha256/{digest.removeprefix('sha256:')}")
        if data is None:
            raise RuntimeError(f"Missing OCI layer blob: {digest}")
        if not isinstance(size, int) or size != len(data):
            raise RuntimeError(f"OCI layer size mismatch: {digest}")
        if hashlib.sha256(data).hexdigest() != digest.removeprefix("sha256:"):
            raise RuntimeError(f"OCI layer digest mismatch: {digest}")

    root_descriptors = index.get("manifests")
    if not isinstance(root_descriptors, list) or not root_descriptors:
        raise RuntimeError("OCI index has no manifests")
    for root_descriptor in root_descriptors:
        visit(root_descriptor)
    expected = [
        "/app/.venv/bin/uvicorn",
        "app.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
    ]
    if not manifests or any(
        config.get("config", {}).get("Cmd") != expected for config in manifests
    ):
        raise RuntimeError("OCI image config lacks the expected uvicorn command")


def validate_scripts_component(
    project: Path, environment: Mapping[str, str] | None = None
) -> None:
    command_environment = environment or os.environ.copy()
    run(
        [
            "uv",
            "run",
            "--project",
            "scripts",
            "utility-scripts",
            "--name",
            "integration",
        ],
        project,
        command_environment,
    )
    run(
        [
            "uv",
            "run",
            "--project",
            "scripts",
            "python",
            "scripts/main.py",
            "--help",
        ],
        project,
        command_environment,
    )


def validate_kmp_component(project: Path) -> None:
    classes = (
        project
        / "kmp"
        / "composeApp"
        / "build"
        / "classes"
        / "kotlin"
        / "desktop"
        / "main"
    )
    if not classes.is_dir() or not any(classes.rglob("*.class")):
        raise RuntimeError(f"KMP desktop compilation produced no classes: {classes}")


def assert_artifacts(
    case: IntegrationCase, project: Path, environment: Mapping[str, str] | None = None
) -> None:
    marker = f"Integration {case.name.title()}"
    if case.family in {"react", "astro"}:
        validate_static_dist(project, marker)
    elif case.family == "hono":
        validate_hono_bundle(project, environment)
    elif case.family == "tauri":
        validate_tauri_bundles(project, environment)
    elif case.family == "fastapi":
        validate_fastapi_oci(project)
    elif case.family == "kmp":
        validate_kmp_component(project)
    else:
        validate_scripts_component(project, environment)


def validate(case: IntegrationCase, source: Path, workspace: Path) -> None:
    project = workspace / case.name
    run_copy(
        str(source),
        project,
        data={"project_name": f"Integration {case.name.title()}", **case.answers},
        defaults=True,
        quiet=True,
    )

    environment = os.environ.copy()
    environment.pop("VIRTUAL_ENV", None)
    if case.family == "tauri":
        environment["APPIMAGE_EXTRACT_AND_RUN"] = "1"

    run(["git", "init", "--initial-branch=main"], project, environment)
    run(["git", "add", "."], project, environment)
    run(
        [
            "git",
            "-c",
            "user.name=Generated Integration",
            "-c",
            "user.email=generated-integration@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-m",
            "generated fixture",
        ],
        project,
        environment,
    )

    run(["devbox", "run", "init"], project, environment)
    if case.e2e_component:
        install_arguments = [
            "bun",
            "run",
            "--cwd",
            case.e2e_component,
            "playwright",
            "install",
        ]
        if environment.get("CI"):
            install_arguments.append("--with-deps")
        install_arguments.append("chromium")
        run(
            install_arguments,
            project,
            environment,
        )
    for command in ("check", "test", "build"):
        run(["devbox", "run", command], project, environment)
    if case.e2e_component:
        run(["devbox", "run", "test:e2e"], project, environment)
    assert_artifacts(case, project, environment)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render and validate generated component projects."
    )
    parser.add_argument("case", choices=[*CASES, "all", *CASE_GROUPS])
    arguments = parser.parse_args()
    if arguments.case == "all":
        selected = CASE_LIST
    elif arguments.case in CASE_GROUPS:
        selected = CASE_GROUPS[arguments.case]
    else:
        selected = (CASES[arguments.case],)

    with TemporaryDirectory(prefix="shared-template-integration-") as temporary:
        workspace = Path(temporary)
        source = workspace / "template-source"
        source.mkdir()
        copy2(ROOT / "copier.yml", source)
        copytree(ROOT / "template", source / "template")
        for case in selected:
            validate(case, source, workspace)


if __name__ == "__main__":
    main()
