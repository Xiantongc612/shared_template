# Implementation Plan

The repository tooling, Copier questionnaire, shared files, update coverage,
component generators, generated project commands, and GitHub Actions automation
are implemented. Cloudflare infrastructure and release automation are implemented
for the Hono and Astro generators.

## Constraints

- A generated project must select at least one of frontend, client, or backend.
- Frontend, client, Hono, and FastAPI outputs remain independent and composable.
- React and Astro are mutually exclusive frontend variants.
- Hono and FastAPI may be selected independently or together.
- Optional integrations are opt-in and scoped to their component.
- Generated configuration, dependencies, files, documentation, commands, and CI
  steps must not mention unselected components.
- `.copier-answers.yml` question names and answer shapes are an update API; add
  compatibility tests and migrations before changing them.
- Generated direct dependencies use exact versions and generated lockfiles are
  not part of the template output.
- Mainline CI renders React, Astro, Tauri, Hono, and FastAPI projects independently
  and runs their generated checks, tests, and local artifact builds.
- Local checks and artifact builds must not deploy, publish packages, push images,
  or mutate remote resources.

## Cloudflare Deployment Milestone

### Approved contracts

- Cloudflare deployment is a core target for Hono and Astro rather than an
  optional questionnaire integration.
- Hono remains a Cloudflare Worker. OpenTofu owns the Worker resource, while
  Wrangler bundles and releases Worker versions so application code is not stored
  in OpenTofu state.
- Astro remains a statically generated site. OpenTofu owns the Cloudflare Pages
  project, and Wrangler uploads `frontend/dist/`; no Cloudflare adapter, Pages
  Functions, or server-side rendering is added.
- Staging and production use separate Worker resources, Pages projects, OpenTofu
  roots, and state. Component infrastructure remains independent rather than
  introducing shared service orchestration.
- Pushes to `main` release to staging. `v*` tags release to production through
  GitHub environments so production approvals and credentials can be isolated.
- OpenTofu uses a partially configured remote backend. Backend configuration,
  Cloudflare credentials, account identifiers, and other environment-specific
  values are supplied outside generated source and are never committed.

### Implemented scope

- The questionnaire adds an update-compatible, validated Cloudflare project
  identifier only for Hono and Astro selections.
- Generated Hono and Astro projects pin OpenTofu, the Cloudflare provider, and
  Wrangler exactly where required.
- Each component owns separate staging and production OpenTofu roots backed by
  environment-specific Cloudflare R2 state.
- Local commands format, initialize with `-backend=false`, validate, test, and
  build without remote mutations.
- A conditional GitHub workflow serializes each environment, applies
  infrastructure, builds locally, and releases through Wrangler. `main` targets
  staging and `v*` tags target the protected production environment.
- Generated and component documentation covers R2 bootstrap, token permissions,
  GitHub environments, release behavior, and rollback.
- Render, historical update, conditional output, exact pin, workflow, and focused
  generated integration coverage enforce these contracts.

## Future Design Decisions

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
