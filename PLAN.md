# Plan

The repository tooling, Copier questionnaire, shared files, update coverage,
component generators, generated project commands, and GitHub Actions automation
are implemented. Cloudflare infrastructure and release automation for the Hono
and Astro generators are implemented. Semgrep static application security
testing is implemented as shared tooling for the repository and generated
projects. The repository hygiene milestone brought the repository to the same
validation and pinning discipline it generates. The dependency automation
milestone automates updates with Dependabot for the repository and generated
projects. The active milestone restructures generated automation into staged
validate, release, and deploy pipelines and aligns repository Devbox commands
with the generated project surface.

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
- Repository and generated projects expose consistent Devbox command names and
  responsibilities; the repository `check` and `test` split mirrors the
  generated project contract.
- Generated deployment automation is a chain of validate, release, and deploy
  workflows that never runs for pull requests. Production requires manual
  approval at both the release publish step and the production deploy step.

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

## Repository Hygiene Milestone

### Approved contracts

- The repository follows the same exact-pinning and validation discipline that
  generated projects receive.
- The repository `check` command scans the same categories of source that it
  tests, so static analysis is not a token step.
- The generated integration matrix is a single source of truth for case
  metadata; no second definition may drift from it.
- The repository release policy in `docs/maintenance.md` is backed by runnable
  automation rather than documentation alone.
- `pre-commit` and `devbox run check` stay consistent in what they validate for
  the repository.
- The repository exposes the same `check` and `test` split that generated
  projects receive.

### Remaining work

None.

### Implemented scope

- The repository Devbox packages are pinned to the same exact versions as the
  generated pins in `template/_versions.jinja`, and a synchronization test
  guards the shared tooling set against drift.
- The repository `.semgrepignore` overrides Semgrep's default test-file
  exclusions so `devbox run check` scans the repository Python sources including
  the test suite, while still skipping Jinja templates and generated artifacts.
- A drift-guard test asserts the generated integration workflow matrix matches
  the case definitions in `scripts/generated_integration.py`.
- The repository pre-commit configuration covers gitleaks, actionlint, and Ruff
  at the same pinned versions `devbox run check` uses.
- A repository release workflow validates the template on `v*` tags and publishes
  a GitHub Release, matching the documented release policy.
- The repository exposes separate `check` and `test` commands that mirror the
  generated project contract, and the repository workflows run both.

## Dependency Automation Milestone

### Approved contracts

- Dependabot owns GitHub Actions updates for the repository and every generated
  project, matching the existing SHA-pinning and reviewed-version-comment
  discipline.
- The repository Dependabot config additionally enables the `uv` and
  `pre-commit` ecosystems. A `pre-commit` rev bump must be mirrored into
  `devbox.json` and `template/_versions.jinja` before the update is merged.
- Generated projects configure component-aware ecosystems (`bun`, `cargo`,
  `uv`, and `opentofu`) so Dependabot coverage tracks the selected components.
  The template never emits lockfiles or an ecosystem for an unselected
  component. Lockfile-based updates stay inert until a project owner commits
  the generated lockfiles, which is their choice.
- Devbox pins and generated `template/_versions.jinja` pins remain on the manual
  update procedure in `docs/maintenance.md` because Dependabot cannot parse
  either file.
- Patch-update auto-merge is enabled for `dependabot[bot]` pull requests only,
  pins `dependabot/fetch-metadata` by full commit SHA, and never touches
  deployment or publication behavior.

### Implemented scope

- The repository `.github/dependabot.yml` enables `github-actions`, `uv`, and
  `pre-commit` on a daily schedule with bounded pull request limits.
- The repository `.github/workflows/auto-merge.yml` auto-merges Dependabot patch
  updates behind the `dependabot[bot]` actor guard.
- `template/.github/dependabot.yml.jinja` renders `github-actions` always and
  `bun`, `cargo`, `uv`, and `opentofu` only for selected components.
- `template/.github/workflows/auto-merge.yml.jinja` renders the same guarded
  patch auto-merge for every generated project, using the
  `dependabot/fetch-metadata` SHA pinned in `template/_versions.jinja`.
- `docs/maintenance.md` documents the Dependabot-owned versus manual update
  split and the `pre-commit` cross-pin requirement.
- Tests cover the root and rendered Dependabot configuration, the
  component-conditional ecosystem set, the auto-merge guard, and the
  `fetch-metadata` pin.

## Release Pipeline Milestone

### Approved contracts

- The repository and generated projects expose consistent Devbox commands:
  `init`, `fmt`, `check`, `test`, and `build` (plus `test:e2e` when
  applicable). The repository `fmt` command formats Python sources with Ruff and
  the repository `build` command packages the template archive, mirroring the
  generated project command surface.
- Generated projects chain three GitHub Actions workflows by `workflow_run`
  completion: `validate` (checks, unit tests, and optional browser tests),
  `release` (artifact builds and GitHub Release publication), and `deploy`
  (Cloudflare infrastructure and Wrangler releases). None of the chained
  workflows runs for pull requests.
- Pull requests run validation only. They never build artifacts or deploy.
- The `release` stage runs for both staging (`main` pushes) and production
  (`v*` tags). Staging builds and uploads artifacts without creating a GitHub
  Release; production additionally requires manual approval before publishing
  a GitHub Release.
- The `deploy` stage consumes the artifacts built by the `release` stage
  instead of rebuilding, applies component infrastructure with OpenTofu, and
  then runs Wrangler release commands. Staging deploys automatically and
  production requires GitHub environment approval.
- Manual approval is required twice for production: at the release publish
  step and at the deploy step.
- Chained workflows derive the environment, deployment mode, checkout SHA, and
  Wrangler version tag from the triggering `workflow_run` run rather than the
  runner's own ref, and guard on the triggering run's conclusion and event
  type so they never execute for pull requests.

### Remaining work

None.

### Implemented scope

- The repository Devbox environment exposes `fmt` (Ruff formatting) and `build`
  (template archive packaging) commands that mirror the generated project
  command surface, and the repository release workflow runs `devbox run build`.
- Generated projects render chained `validate`, `release`, and `deploy`
  workflows connected by `workflow_run` completion; the superseded check, test,
  build, and cloudflare-deploy workflow templates were removed.
- Pull requests run only the read-only validate stage. The release stage builds
  and uploads artifacts on `main` for staging and on `v*` tags for production,
  where a production-environment approval gate protects the GitHub Release
  publish job. The deploy stage downloads the release-built artifacts, applies
  component OpenTofu infrastructure, and runs Wrangler release commands;
  production deploy requires a second GitHub environment approval.
- Chained workflows check out the triggering commit, derive the deployment mode
  and environment from the triggering run's branch, and pass the triggering
  run's SHA as the Wrangler version tag. Every chained job guards on the
  triggering run's conclusion and event type so deployment never runs for pull
  requests.
- Tests cover the repository command surface, the chained workflow triggers and
  guards, the production-only publish gate, artifact consumption by the deploy
  stage, cache safety, and rendered actionlint validity.

## Workflow Cache and Concurrency Milestone

### Approved contracts

- Every repository and generated workflow scopes concurrency to a named group.
  Validation and auto-merge groups cancel superseded runs, while release and
  deploy groups never cancel an active publication or deployment.
- Cache steps cover download stores (Bun, Cargo, uv, Playwright) and Docker
  layers only. They never cache credentials, `node_modules`, virtual
  environments, Cargo targets, OpenTofu state, or resolved backend configuration.
- Every cache step provides a `restore-keys` prefix fallback so a superseded
  lockfile or version hash still restores the previous download store and only
  the changed parts are re-downloaded.

### Remaining work

None.

### Implemented scope

- The repository `integration` workflow and the generated `validate`, `release`,
  and `deploy` workflows cache Bun, Cargo, uv, and Playwright download stores
  with `restore-keys` prefix fallbacks.
- The repository `validate` workflow caches the uv download store used by the
  `check` and `test` commands.
- Repository and generated workflows keep concurrency groups and
  `cancel-in-progress` policies consistent with their publication sensitivity.
- Tests cover cache path safety, `restore-keys` prefix fallbacks, and repository
  workflow concurrency.

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
