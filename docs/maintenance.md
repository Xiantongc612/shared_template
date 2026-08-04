# Maintenance and releases

## Dependency updates

Repository Python dependencies are constrained in `pyproject.toml` and resolved
in `uv.lock`. Devbox packages are resolved in `devbox.lock`. Generated component
manifests use exact direct dependency versions, while generated Cargo transitive
dependencies are resolved by Cargo when the client is initialized.

Update one ecosystem at a time:

1. Update the declared version or run the ecosystem's update command.
2. Refresh only the associated lockfile.
3. Run `devbox run check` and `pre-commit run --all-files`.
4. Render and build every component affected by the update without deploying or publishing it.
5. Commit the update separately from behavioral template changes.

Use `devbox update <package>` for repository Devbox packages and `uv lock
--upgrade-package <package>` for one repository Python dependency. Generated
JavaScript and Python versions are updated directly in their component template
and validated through the render matrix plus a local artifact build.

## Copier compatibility

Question names and answer shapes form the update API. Before changing either,
add an update test that starts from the previous `.copier-answers.yml` shape.
Prefer adding conditional questions with stable scalar answers over replacing
existing questions. A rename, type change, changed choice value, or removed
answer requires a Copier migration and a major template release.

Copier itself is tested through the representative tagged-template update test.
Upgrade Copier separately and run the complete matrix before accepting a new
minimum version.

## Versioning

Template releases use semantic versioning:

- Patch: fixes that preserve questionnaire and generated-project contracts.
- Minor: backward-compatible questions, integrations, and generated files.
- Major: questionnaire answer incompatibility, moved artifact boundaries, or removed generated behavior.

Template release tags must be PEP 440-compatible so Copier can order template
versions. Every template release must pass CI from a clean checkout.

Generated projects include separate check, test, build, and GitHub Release
workflows. Their release workflow publishes selected artifacts to a GitHub
Release from a `v*` tag. Tauri automation produces Linux AppImage and Debian
bundles only because macOS and Windows artifacts require native runners. OCI and
Cloudflare artifacts are built locally without registry publication or deployment.
