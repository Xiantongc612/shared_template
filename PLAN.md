# Plan

The repository tooling, Copier questionnaire, shared files, update coverage,
component generators, generated project commands, and GitHub Actions automation
are implemented. Cloudflare infrastructure and release automation for the Hono
and Astro generators are implemented. Semgrep static application security
testing is implemented as shared tooling for the repository and generated
projects. The repository hygiene milestone brought the repository to the same
validation and pinning discipline it generates. The dependency automation
milestone automates updates with Dependabot for the repository and generated
projects. The release pipeline milestone restructured generated automation
into staged validate, release, and deploy workflows and aligned repository
Devbox commands with the generated project surface. The workflow cache and
concurrency milestone scopes workflow concurrency, adds prefix-restore
download caches with opt-out toggles, and migrates Linux CI and native
artifact builds to Ubuntu 24.04. The Python scripts component milestone adds an
independently selectable utility-scripts workspace with opt-in local data
analysis and DuckDB integrations and no deployable or release artifact.

## Constraints

- A generated project must select at least one of frontend, client, backend,
  Python scripts, or Kotlin Multiplatform.
- Frontend, client, Hono, FastAPI, Python scripts, and Kotlin Multiplatform outputs remain independent
  and composable.
- React and Astro are mutually exclusive frontend variants.
- Hono and FastAPI may be selected independently or together.
- The Python scripts component produces a local utility workspace and never a
  deployable or release artifact; its `build` stage validates source
  compilation only.
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
  Hono, FastAPI, Python scripts, and Kotlin Multiplatform independently. It runs generated checks,
  tests, applicable browser tests, local builds, and semantic artifact
  validation.
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
- Caching is opt-out and defaults to enabled. The questionnaire always asks
  `cache_nix`, `cache_docker`, and `cache_downloads`; each toggle removes only
  its own cache surface and never the build behavior itself.
- `cache_downloads` gates the Bun, Cargo, uv, and Playwright download-store
  steps, `cache_nix` gates the Devbox Nix store cache, and `cache_docker` gates
  the FastAPI build cache arguments passed to `docker buildx build`.
- Linux CI and native artifact builds run on Ubuntu 24.04, where the Devbox Nix
  toolchain links against glibc 2.39. Tauri AppImage bundling installs
  `libfuse2t64`.

### Remaining work

None.

### Implemented scope

- The repository `integration` workflow and the generated `validate`, `release`,
  and `deploy` workflows cache Bun, Cargo, uv, and Playwright download stores
  with `restore-keys` prefix fallbacks.
- The repository `validate` workflow caches the uv download store used by the
  `check` and `test` commands.
- Generated workflows render the opt-out cache toggles: `cache_downloads`
  removes download-store steps, `cache_nix` sets `enable-cache: false` on the
  Devbox installer, and `cache_docker` clears `DOCKER_CACHE_ARGS` for FastAPI
  builds.
- Repository and generated workflows run on `ubuntu-24.04`; generated and
  repository Tauri builds install `libfuse2t64`.
- Repository and generated workflows keep concurrency groups and
  `cancel-in-progress` policies consistent with their publication sensitivity.
- Tests cover the runner pin, the opt-out cache toggles, cache path safety,
  `restore-keys` prefix fallbacks, and repository workflow concurrency.

## Python Scripts Component Milestone

### Approved contracts

- The Python scripts component is an independently selectable and composable
  component that generates a local utility-scripts workspace under `scripts/`.
  A generated project must select at least one of frontend, client, backend, or
  Python scripts.
- The workspace uses uv as the package manager and Python as the runtime, with
  the same shared tooling as every generated project: Devbox (gitleaks,
  actionlint, Semgrep, pre-commit) plus pytest, Ruff, and ty.
- The distribution, import package, and console script use fixed names
  (`utility-scripts`, `utility_scripts`, and a `utility-scripts` entry point)
  following the fixed-name pattern of the other generated components.
- `python_data_analysis` is an opt-in toggle that adds `pandas`, `numpy`,
  `matplotlib`, and `jupyter` for local data analysis. `python_duckdb` is a
  separate opt-in toggle that adds `duckdb`. Both are gated on the Python
  scripts component, disabled by default, and emit no configuration,
  dependencies, files, or documentation when unselected.
- The Python scripts component has no deployable or release artifact. Its
  `build` command validates that the package sources compile, and generated
  release automation skips artifact collection and GitHub Release publication
  when no selected component produces an artifact.
- Generated Devbox commands mirror the component contract: `init` syncs the uv
  environment, `fmt` formats sources with Ruff, `check` runs Ruff and ty,
  `test` runs pytest, and `build` compiles the sources. The uv download-store
  cache is a single conditional workflow step shared with FastAPI keyed on
  `**/pyproject.toml`.
- The integration matrix renders minimal and optional-integration variants of
  the Python scripts component and validates them by executable behavior rather
  than a built artifact.

### Remaining work

None.

### Implemented scope

- The Copier questionnaire adds the `Python Scripts` component choice (value
  `scripts`) and the gated `python_data_analysis` and `python_duckdb` toggles,
  and the component-selection validator now accepts a Python scripts-only
  project.
- `template/_versions.jinja` pins `pandas`, `numpy`, `matplotlib`, `jupyter`,
  `duckdb`, and `hatchling`, reusing the existing `python`, `python_runtime`,
  `uv`, `pytest`, `ruff`, and `ty` pins.
- `template/scripts/` renders the `utility-scripts` package with a `cli` module,
  conditional `analysis` and `data` modules, and matching tests.
- Shared templates emit the scripts component's Devbox packages and commands,
  Python Semgrep rules, gitignore entries, Dependabot uv ecosystem, combined uv
  download-store caches, and the artifact-free release path, without mentioning
  the component when unselected.
- The integration harness adds `scripts` and `scripts-integrations` cases and a
  validator that runs the generated console script.
- Tests cover the questionnaire gates, generator files, exact dependency pins,
  component-aware Semgrep rules, Dependabot coverage, workflow caching and the
  artifact-free release path, and the integration case matrix.

## Kotlin Multiplatform Component Milestone

### Approved contracts

- Kotlin Multiplatform is a new independently selectable component with the
  stable Copier value `kmp` and output boundary `kmp/`. It does not replace or
  alter the existing Tauri `client` component and may be selected alongside it.
- The component is an application generator using Compose Multiplatform for
  shared UI and shared logic. It does not share source with the frontend or
  client components.
- Supported targets are Android (API 24), iOS (iOS 15, device arm64 and Apple
  Silicon simulator), macOS (macOS 13, arm64), and Windows (Windows 10, x64).
  Desktop targets use Compose Desktop/JVM; Kotlin/Native desktop targets are
  not generated.
- `kmp_identifier` is a required-on-selection, validated reverse-domain
  identifier used to derive Kotlin, Android, iOS, macOS, and Windows identity
  metadata. It remains distinct from `client_identifier`.
- Generated local and pull-request commands compile and test common, Android,
  and desktop JVM sources on Ubuntu. Apple and native Windows packaging is not
  part of normal Linux integration validation.
- `build` is non-publishing and produces compile/test build outputs only. It
  never signs, notarizes, uploads, or publishes an application.
- A generated `package-kmp` workflow is manually dispatched and uploads unsigned
  Android APK, macOS DMG, and Windows MSI artifacts as GitHub Actions artifacts.
  It also compiles the iOS Apple Silicon simulator application but does not
  publish it. It does not create or modify GitHub Releases.
- Gradle dependency downloads may be cached through the existing opt-out
  `cache_downloads` toggle. Project Gradle state, build outputs, credentials,
  and signing material are never cached.
- The component has no Cloudflare deployment, application-store publication,
  signing, notarization, or cross-component orchestration behavior.

### Implemented scope

- The questionnaire, answer compatibility coverage, generated Gradle/Compose
  project, Devbox commands, Semgrep rules, Dependabot configuration, generated
  documentation, and component-specific gitignore entries are implemented.
- Generated validation includes Kotlin/Gradle checks and tests without building
  platform packages on Linux. The repository integration matrix includes a
  Linux KMP case with semantic validation of Linux-compatible build outputs.
- Generated workflows include safe Gradle download caching and a manually
  dispatched, read-only packaging workflow for unsigned platform artifacts.

### Remaining work

- Native packaging can only be exercised on the corresponding macOS and Windows
  runners; Linux repository validation covers rendering, workflow semantics, and
  Linux-compatible compilation.

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
- A universal generated-project directory layout.
- Resolution of 1Password references into generated files or logs.
- SonarQube or SonarCloud server-based static analysis.
