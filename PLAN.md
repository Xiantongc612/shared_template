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

### Remaining work

1. Pin Semgrep in the repository Devbox packages and add the Semgrep scan step to
   the repository `check` command.
2. Add the repository `semgrep.yml` rule file with a Python and generic-security
   rule set that excludes Jinja templates.
3. Add a Semgrep pin to `template/_versions.jinja` and a generated
   `semgrep.yml.jinja` template with component-aware rules.
4. Add the Semgrep scan step to the generated `check` command and the Semgrep
   package to the generated Devbox packages.
5. Document Semgrep in the shared tooling lists of the repository and generated
   README files, and record the rule-refresh procedure in `docs/maintenance.md`.
6. Add tests covering the root and generated pins, the component-aware generated
   rule file, and the presence of the Semgrep step in root and generated `check`
   commands.

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
