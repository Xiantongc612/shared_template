# Maintenance and releases

## Dependency updates

Repository Python dependencies are constrained in `pyproject.toml` and resolved
in `uv.lock`. Devbox packages are resolved in `devbox.lock`. Generated component
manifests use exact direct dependency versions and do not include committed
lockfiles. Initialization creates local Devbox, Bun, uv, and OpenTofu lockfiles,
while Cargo creates its local lockfile on first resolution; generated projects
ignore these files. Transitive dependency versions remain ecosystem-resolved.

## Dependabot

Dependabot owns GitHub Actions updates for the repository and every generated
project. The repository `.github/dependabot.yml` additionally enables the `uv`
and `pre-commit` ecosystems. When Dependabot bumps a `pre-commit` revision,
mirror the same version into `devbox.json` and `template/_versions.jinja` before
merging the pull request.

Generated projects render a component-aware `.github/dependabot.yml` covering
`github-actions` plus `bun`, `cargo`, `uv`, and `opentofu` for selected
components. These lockfile-based ecosystems stay inactive until a project owner
commits the generated lockfiles, which `.gitignore` excludes by default;
Dependabot then proposes updates directly in the generated project.

Dependabot patch updates are auto-merged for `dependabot[bot]` pull requests by
the repository and generated `auto-merge.yml` workflows, which pin
`dependabot/fetch-metadata` by full commit SHA.

Devbox pins and the generated pins in `template/_versions.jinja` are not
parseable by Dependabot and remain on the manual procedure below.

Update one ecosystem at a time:

1. Update the declared version or run the ecosystem's update command.
2. Refresh the repository lockfile when updating repository tooling. Generated
   dependency updates do not add lockfiles to the template.
3. Run `devbox run check`, `devbox run test`, and `pre-commit run --all-files`.
4. Render and build every component affected by the update without deploying or publishing it.
5. Commit the update separately from behavioral template changes.

Use `devbox update <package>` for repository Devbox packages and `uv lock
--upgrade-package <package>` for one repository Python dependency. Generated
dependency and tool versions are updated in `template/_versions.jinja` and
validated through the render matrix plus a local artifact build.

The repository Semgrep package is pinned in `devbox.json` and the generated
Semgrep package is pinned in `template/_versions.jinja`. Keep both versions in
sync when updating Semgrep.

## Semgrep rules

The repository scans with the committed `semgrep.yml` rule file, and generated
projects scan with a component-aware rule file emitted from
`template/semgrep.yml.jinja`. Rules are vendored so `devbox run check` stays
offline and deterministic; no registry download or result upload is performed.
The repository `.semgrepignore` overrides Semgrep's default test-file exclusions
so the root scan covers repository Python sources including the test suite while
still skipping Jinja templates and generated artifacts. Keep that file in sync
when repository source layouts change.

To refresh the rule sets, render a representative generated project, run
`semgrep scan --config auto` with a scratch profile to compare coverage, then
fold any new high-value, low-false-positive patterns into `semgrep.yml` and
`template/semgrep.yml.jinja`. Validate with
`semgrep scan --validate --config <file>` and confirm the repository and
generated scans still pass with zero unexpected findings. Commit the rule
update separately from behavioral template changes.

## Copier compatibility

Question names and answer shapes form the update API. Before changing either,
add an update test that starts from the previous `.copier-answers.yml` shape.
Prefer adding conditional questions with stable scalar answers over replacing
existing questions. A rename, type change, changed choice value, or removed
answer requires a Copier migration and a major template release.

Copier itself is tested through the representative tagged-template update test.
Upgrade Copier separately and run the complete matrix before accepting a new
minimum version.

## Generated integration

`devbox run check` validates repository source and deterministic template
rendering, and `devbox run test` runs the repository test suite. `devbox run
integration` additionally renders React, Astro, Tauri, Hono, and FastAPI
projects independently, then runs each generated project's
`init`, `check`, `test`, and `build` commands. Focused `integration:<component>`
commands support local maintenance.

The generated integration matrix runs on pushes to `main` and can be dispatched
manually. Tauri validation requires Linux desktop build libraries and both Debian
and AppImage bundles. FastAPI artifact validation requires Docker Buildx and a
valid OCI archive. These builds remain local validation and do not deploy or
publish artifacts.

## Versioning

Template releases use semantic versioning:

- Patch: fixes that preserve questionnaire and generated-project contracts.
- Minor: backward-compatible questions, integrations, and generated files.
- Major: questionnaire answer incompatibility, moved artifact boundaries, or removed generated behavior.

Template release tags must be PEP 440-compatible so Copier can order template
versions. Every template release must pass CI from a clean checkout.

The repository `.github/workflows/release.yml` validates the template and
publishes a GitHub Release from a `v*` tag. To cut a release, create and push
the version tag (for example `git tag v0.2.0 && git push origin v0.2.0`); the
workflow runs the full repository check and attaches the template archive. The
release workflow is not a deployment and does not modify remote resources beyond
the GitHub Release.

Generated projects chain a `validate` workflow (checks, unit tests, and
optional browser tests), a `release` workflow (artifact builds and GitHub
Release publication), and a `deploy` workflow (Cloudflare) connected by
`workflow_run` completion. Pull requests run the read-only validate stage only.
The release stage builds and uploads artifacts for `main` pushes and, on `v*`
tags, publishes a GitHub Release behind a production approval. The deploy stage
downloads the release-built artifacts, applies component infrastructure with
OpenTofu, and runs Wrangler release commands; staging deploys automatically and
production requires a separate GitHub environment approval. Tauri automation
produces Linux AppImage and Debian bundles only because macOS and Windows
artifacts require native runners. OCI and Cloudflare artifacts are built locally
without deployment by the validate and release stages.
