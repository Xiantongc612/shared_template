# Plan

The repository tooling, Copier questionnaire, shared files, update coverage,
component generators, generated project commands, and GitHub Actions automation
are implemented. Cloudflare infrastructure and release automation for the Hono
and Astro generators are implemented. The active milestone adds Semgrep static
application security testing as shared tooling for the repository and generated
projects.

## Constraints

- A generated project must select at least one of frontend, client, or backend.
- Frontend, client, Hono, and FastAPI outputs remain independent and composable.
- React and Astro are mutually exclusive frontend variants.
- Hono and FastAPI may be selected independently or together.
- Optional integrations are opt-in and scoped to their component.
- Semgrep is shared tooling (like Gitleaks and actionlint), not an optional
  integration. It is always enabled for the repository and every generated
  project.
- Generated configuration, dependencies, files, documentation, commands, and CI
  steps must not mention unselected components.
- `.copier-answers.yml` question names and answer shapes are an update API; add
  compatibility tests and migrations before changing them.
- Generated direct dependencies use exact versions and generated lockfiles are
  not part of the template output.
- CI renders minimal and optional-integration variants of React, Astro, Tauri,
  Hono, and FastAPI independently. It runs generated checks, tests, applicable
  browser tests, local builds, and semantic artifact validation.
- Local checks and artifact builds must not deploy, publish packages, push images,
  or mutate remote resources.

## Static Analysis Milestone

### Approved contracts

- Semgrep runs entirely locally inside `devbox run check` using a vendored rule
  file; no rule registry download, service account, or result upload is required.
- The repository `check` command runs Semgrep against repository sources with a
  Python and generic-security rule set, excluding Jinja templates that Semgrep
  cannot parse.
- Every generated project's `check` command runs Semgrep against component
  sources with a component-aware rule set: TypeScript/JavaScript for the React
  frontend, Tauri client, and Hono backend; Rust for the Tauri client; Python
  for FastAPI; HCL for Astro and Hono OpenTofu infrastructure.
- Semgrep and rule versions are pinned: the root pin lives in `devbox.json`, the
  generated pin lives in `template/_versions.jinja`, and the vendored rule file
  is committed and refreshed through `docs/maintenance.md`.
- No SonarQube or SonarCloud scanner is introduced because analysis upload and
  server interaction are outside the local, offline `check` contract.

### Implemented scope

- The repository Devbox environment pins Semgrep 1.164.0 and the repository
  `check` command runs `semgrep scan --config semgrep.yml`.
- The committed `semgrep.yml` provides a Python and generic-security rule set;
  Jinja templates are not scanned because Semgrep cannot parse them.
- `template/_versions.jinja` pins the generated Semgrep version, and the
  generated `semgrep.yml.jinja` emits component-aware rules: TypeScript and
  JavaScript for the React frontend, Tauri client, and Hono backend; Rust for
  the Tauri client; Python for FastAPI; and HCL for Astro and Hono OpenTofu
  infrastructure.
- Generated Devbox packages include Semgrep and the generated `check` command
  runs `semgrep scan --config semgrep.yml` with the vendored rules.
- Repository and generated README files list Semgrep as shared tooling, and
  `docs/maintenance.md` documents the Semgrep pin locations and the rule-refresh
  procedure.
- Tests cover the root and generated pins, generated config validity, the
  presence of the Semgrep step in root and generated `check` commands, and
  component-aware rule selection.

## Deferred Design Decisions

The following work is intentionally unplanned until its contracts and compatibility
requirements are approved:

- Mobile targets for the Tauri client.
- Native macOS and Windows Tauri build and release runners.
- Astro server-side rendering and provider-specific adapters.
- Shared UI or source packages between independently generated components.
- Docker Compose or other cross-service orchestration.
- Container registry publication, package publication, or application-store
  release automation.
- Migration of Linux CI and native artifact builds from Ubuntu 22.04.
- A universal generated-project directory layout.
- Resolution of 1Password references into generated files or logs.
- SonarQube or SonarCloud server-based static analysis.
