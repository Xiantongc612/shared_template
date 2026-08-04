# Implementation Plan

The repository tooling, Copier questionnaire, shared files, component generators,
generated project commands, and generated GitHub Actions automation are
implemented. The following integration and maintenance work remains active.

## Active Milestones

1. Clarify that TanStack Query is available only to React-based frontend and
   client components, and align the repository Gitleaks hook with the generated
   project version.
2. Make every generated direct dependency declaration exact. Generated projects
   must not rely on committed lockfiles for their initial dependency resolution.
3. Extend Copier update coverage with a historical answer fixture and an update
   from a tagged older template revision, while preserving the existing answer
   names and shapes.
4. Add repository integration commands that render representative React, Astro,
   Tauri, Hono, and FastAPI projects and run their native checks, tests, and local
   artifact builds without deployment.
5. Run the generated-project integration suite in mainline GitHub Actions. The
   suite must exercise component-specific outputs rather than introducing a
   universal generated layout or cross-service orchestration.

The milestones are complete when repository checks, historical Copier updates,
and generated component validation pass in GitHub Actions. Environment-specific
artifact limitations must be explicit rather than silently skipped.

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
