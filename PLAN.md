# Implementation Plan

The planned repository tooling, Copier questionnaire, shared files, render and
update coverage, component generators, generated project commands, and GitHub
Actions automation are implemented. No active implementation phase remains.

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
- Local checks and artifact builds must not deploy, publish packages, push images,
  or mutate remote resources.

## Future Design Decisions

The following work is intentionally unplanned until its contracts and compatibility
requirements are approved:

- Mobile targets for the Tauri client.
- Native macOS and Windows Tauri build and release runners.
- Astro server-side rendering and provider-specific adapters.
- Shared UI or source packages between independently generated components.
- Docker Compose or other cross-service orchestration.
- Cloudflare deployment, container registry publication, package publication, or
  application-store release automation.
- A universal generated-project directory layout.
- Resolution of 1Password references into generated files or logs.
