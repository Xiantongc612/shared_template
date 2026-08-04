import argparse
import os
import subprocess
import tarfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from shutil import copy2, copytree
from tempfile import TemporaryDirectory
from typing import Any

from copier import run_copy

ROOT = Path(__file__).parents[1]
CASES: dict[str, dict[str, Any]] = {
    "react": {},
    "astro": {"frontend_variant": "astro"},
    "tauri": {"components": ["client"]},
    "hono": {"components": ["backend"], "backend_variants": ["hono"]},
    "fastapi": {"components": ["backend"], "backend_variants": ["fastapi"]},
}


def run(arguments: Sequence[str], cwd: Path, environment: Mapping[str, str]) -> None:
    subprocess.run(arguments, cwd=cwd, env=environment, check=True)


def assert_artifacts(case: str, project: Path) -> None:
    if case in {"react", "astro"}:
        expected = project / "frontend" / "dist" / "index.html"
        if not expected.is_file():
            raise RuntimeError(f"Missing generated artifact: {expected}")
        return

    if case == "hono":
        expected = project / "backend" / "hono" / "dist" / "index.js"
        if not expected.is_file():
            raise RuntimeError(f"Missing generated artifact: {expected}")
        return

    if case == "tauri":
        bundle = project / "client" / "src-tauri" / "target" / "release" / "bundle"
        if not list((bundle / "deb").glob("*.deb")):
            raise RuntimeError("Missing generated Tauri Debian bundle")
        if not list((bundle / "appimage").glob("*.AppImage")):
            raise RuntimeError("Missing generated Tauri AppImage bundle")
        return

    archive = project / "backend" / "fastapi" / "dist" / "fastapi-backend.tar"
    if not archive.is_file():
        raise RuntimeError(f"Missing generated artifact: {archive}")
    with tarfile.open(archive) as contents:
        if not any(Path(member.name).name == "index.json" for member in contents):
            raise RuntimeError(f"Invalid OCI archive: {archive}")


def validate(case: str, source: Path, workspace: Path) -> None:
    project = workspace / case
    run_copy(
        str(source),
        project,
        data={"project_name": f"Integration {case.title()}", **CASES[case]},
        defaults=True,
        quiet=True,
    )

    environment = os.environ.copy()
    if case == "tauri":
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

    for command in ("init", "check", "test", "build"):
        run(["devbox", "run", command], project, environment)
    assert_artifacts(case, project)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render and validate generated component projects."
    )
    parser.add_argument("case", choices=[*CASES, "all"])
    arguments = parser.parse_args()
    selected = CASES if arguments.case == "all" else (arguments.case,)

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
