# Repository Instructions

## Scope and source of truth

- Read `README.md` for the implemented component model and `PLAN.md` for current constraints and deferred design decisions before making architectural changes.
- Keep components independent. Do not invent a universal generated layout, shared UI package, Docker Compose setup, or service orchestration without an explicit design decision.
- Treat frontend, client, Hono, FastAPI, Python scripts, and Kotlin Multiplatform as separate generators with component-specific outputs.
- Do not implement deferred capabilities without an explicit design decision.
- Keep the implemented Cloudflare infrastructure and releases for Hono and static
  Astro component-owned rather than introducing shared runtime dependencies.

## Working method

- Inspect the working tree before editing and preserve unrelated or user-authored changes.
- Make small, reviewable commits. Each commit should represent one coherent change and leave the repository in a valid state.
- Prefer commits in this order when applicable: tooling, questionnaire, shared templates, tests, then one component generator at a time.
- Do not combine broad formatting, dependency upgrades, generated output, and behavioral changes in one commit.
- Run the narrowest relevant checks during development and the full repository check before completing a milestone.
- Use `devbox run check` for repository source and render validation. Use the
  relevant `devbox run integration:<component>` command for generated component
  checks, tests, and artifact builds. Use the matching `*-integrations` command
  for optional integrations; `devbox run integration` runs the full suite.
- Template rendering and local artifact builds are validation. Commands that mutate remote resources are deployments and require explicit user authorization.
- Keep repository tooling pins in `devbox.json` synchronized with the generated
  pins in `template/_versions.jinja`; add or update a synchronization test when
  a shared tool version changes.
- Keep the repository `.semgrepignore`, pre-commit hooks, and integration case
  metadata consistent with their generated or scripted counterparts.

## Copier design rules

- Require at least one of Frontend, Client, Backend, Python Scripts, or Kotlin Multiplatform.
- Use React as the non-interactive default frontend selection.
- Keep React and Astro mutually exclusive frontend variants.
- Allow Hono, FastAPI, or both when Backend is selected; reject an empty backend selection.
- Keep frontend and client optional integrations independently selectable.
- Keep Kotlin Multiplatform under `kmp/` with Compose UI and logic independent from frontend and Tauri source.
- Keep optional integrations disabled by default.
- Treat Semgrep SAST as shared tooling (like Gitleaks and actionlint), always
  enabled for the repository and every generated project with vendored rules.
  Do not implement SonarQube or SonarCloud server-based analysis.
- Derive fixed artifact types from component choices rather than asking users to select them.
- Avoid emitting configuration, dependencies, files, or documentation for unselected components.
- Preserve `.copier-answers.yml` compatibility and add update tests before changing existing question names or answer shapes.
- Keep generated direct dependency declarations exact and do not emit generated
  lockfiles as template output.
- Keep generated dependency and automation pins in `template/_versions.jinja`;
  do not expose them as Copier answers or emit the registry into generated output.
- Ask the `cache_nix`, `cache_docker`, and `cache_downloads` toggles for every
  generated project with caching enabled by default, so caching stays opt-out
  rather than opt-in.
- Keep Astro static for Cloudflare Pages. Do not add the Cloudflare adapter, Pages
  Functions, or server-side rendering as part of the deployment milestone.

## Cloudflare deployment design

- Use separate staging and production Worker resources, Pages projects, OpenTofu
  roots, state, credentials, and GitHub environments.
- Let OpenTofu own the Hono Worker resource and Astro Pages project. Let Wrangler
  bundle and release Hono versions and upload Astro's static `frontend/dist/`
  artifact; do not put application bundles in OpenTofu state.
- Use partial remote-backend configuration and environment-provided credentials.
  Never generate backend credentials, Cloudflare tokens, account identifiers, or
  resolved secret values.
- Keep formatting, checks, tests, builds, and infrastructure validation
  non-deploying. Deployment commands and workflows must be explicit and must not
  run for pull requests.
- Chain generated deployment automation as validate, release, and deploy
  workflows connected by `workflow_run` completion. Release `main` to staging
  and `v*` tags to production. Production requires manual approval at both the
  release publish step and the production deploy step; staging deploys
  automatically after its release build passes.

## Generated automation design

- Pin external GitHub Actions by full commit SHA with a reviewed version comment,
  and pin the Devbox installer CLI and checksum. Run Linux CI and native artifact
  builds on Ubuntu 24.04 with `libfuse2t64` for Tauri AppImage bundling.
- Give validation jobs read-only permissions. Keep write credentials confined to
  publication or deployment steps and jobs that require them.
- Give every job an explicit timeout and concurrency policy. Cancel superseded
  validation, but do not cancel an active publication or deployment.
- Cache download stores and Docker layers only. Never cache credentials,
  `node_modules`, virtual environments, Cargo targets, OpenTofu state, or resolved
  backend configuration. Give every cache step a `restore-keys` prefix fallback so
  a superseded lockfile or version hash still restores the previous download
  store and only the changed parts are re-downloaded. Gradle caches may include
  only dependency modules and wrapper distributions, never project build state.
- Cache toggles are opt-out and default to enabled. The questionnaire always
  asks `cache_downloads` (Bun, Cargo, Gradle, uv, and Playwright download-store steps),
  `cache_nix` (Devbox Nix store cache), and `cache_docker` (FastAPI
  `DOCKER_CACHE_ARGS`); each toggle removes only its own cache surface and never
  the build behavior itself. Never cache Cargo `target/` directories.
- Validate generated workflows with actionlint and validate built artifacts by
  structure or executable behavior rather than filename existence alone.
- Chained release and deploy workflows run on the default branch, check out the
  triggering commit, derive the environment from the triggering run's branch,
  and guard on the triggering run's conclusion and event type so they never
  execute for pull requests. Deploy stages consume the artifacts built and
  validated by the release stage instead of rebuilding.

## Secrets and 1Password on Windows

Codex commands run in a non-interactive shell and do not load the `op` function from `~/.zshrc`. If a user explicitly authorizes a command that requires repository secrets, obtain the service-account token with the Windows 1Password CLI and invoke the Linux CLI explicitly:

```sh
OP_SERVICE_ACCOUNT_TOKEN="$(op.exe read 'op://Infrastructure/1Password Service Token/credential')" \
  /usr/bin/op run --env-file=.env.op -- <command>
```

- The `op.exe` call uses the WSL-to-Windows bridge and may require execution outside the Codex sandbox.
- Never print, log, inspect, or persist `OP_SERVICE_ACCOUNT_TOKEN`.
- Never replace references in `.env.op` with resolved plaintext.
- Do not access 1Password for ordinary development, tests, linting, template rendering, or local builds.
- If any secret value is exposed in command output or otherwise read directly, stop immediately, do not continue processing it, and notify the user.

## Deployment safety

- Treat deployment workflows and any command that mutates remote resources as
  deployment operations.
- Do not run deployment commands, publish artifacts, push images, or mutate Cloudflare or other remote resources unless the user explicitly asks for that operation.
- Do not interpret a request to test or validate as permission to deploy.

## Completion expectations

- Run `git diff --check` for edited files.
- Run relevant formatters, linters, type checks, and tests available for the changed scope.
- Report checks that could not be run and why.
- Confirm the staged diff before every commit so unrelated files are not included.
- Use descriptive commit messages and report the resulting commit hash.
