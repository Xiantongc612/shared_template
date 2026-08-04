# Implementation Plan

The repository tooling, Copier questionnaire, shared files, update coverage,
component generators, generated project commands, and GitHub Actions automation
are implemented. The active milestone adds Cloudflare infrastructure and release
automation for the existing Hono and Astro generators.

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

### Remaining work

1. Add a Cloudflare-safe project identifier and its validation to the Copier
   questionnaire without changing existing answer names or shapes. Add update
   coverage for the new answer.
2. Add exact OpenTofu, Cloudflare provider, and Astro Wrangler pins only when the
   selected components require them.
3. Generate component-owned OpenTofu modules and separate staging and production
   roots for Hono Workers and Astro Pages projects. Include formatting and local
   validation commands that cannot mutate remote resources.
4. Add matching staging and production release configuration to Hono and Astro.
   Preserve the existing local artifact commands as non-deploying builds and keep
   Astro's output static.
5. Generate a conditional Cloudflare deployment workflow for selected Hono and
   Astro components. Serialize deployments per environment, apply infrastructure,
   build locally, and release with Wrangler using environment-scoped credentials.
6. Document backend bootstrap, required token permissions, GitHub environments,
   staging and production release behavior, and rollback procedures in generated
   projects and component documentation.
7. Add render and update tests for conditional output, independent environment
   state, exact pins, least-privilege workflows, and the absence of deployment
   residue from unselected components.
8. Extend Hono and Astro integration validation with `tofu fmt -check`,
   `tofu init -backend=false`, and `tofu validate`. Keep integration tests local
   and finish with the full repository check and generated integration suite.

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
