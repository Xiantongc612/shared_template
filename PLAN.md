# Plan

There are no approved implementation milestones. The constraints below remain in
force, and proposed capabilities remain deferred until their contracts and
compatibility requirements are approved.

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
- CI renders minimal and optional-integration variants of React, Astro, Tauri,
  Hono, and FastAPI independently. It runs generated checks, tests, applicable
  browser tests, local builds, and semantic artifact validation.
- Local checks and artifact builds must not deploy, publish packages, push images,
  or mutate remote resources.

## Deferred Design Decisions

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
