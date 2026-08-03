# Implementation Plan

This plan implements the component model documented in `README.md` without prematurely imposing a repository-wide generated layout, shared UI architecture, or service orchestration model.

## Guiding constraints

- A generated project must select at least one of frontend, client, or backend.
- Frontend, client, and backend components are independent and composable.
- React and Astro are mutually exclusive frontend variants.
- Hono and FastAPI may be selected independently or together.
- Optional integrations are opt-in and scoped to their component.
- Artifact types are fixed by component:
  - Frontend: provider-neutral static-site artifacts.
  - Client: Tauri desktop and/or mobile application bundles.
  - Hono: Cloudflare edge-function artifact.
  - FastAPI: OCI-compatible container artifact.
- Component paths and internal layouts must be designed when that component is implemented. Do not infer a common layout, shared UI package, Compose file, or orchestration layer.

## Phase 1: Repository tooling baseline

Goal: make development and validation reproducible before implementing template behavior.

- Review the existing Devbox, uv, Python package, and pre-commit configuration.
- Add Copier, pytest, Ruff, and ty as locked development dependencies.
- Keep `shared_template` as the package for template-development helpers and tests, not generated application code.
- Extend `devbox run check` to run:
  - Gitleaks.
  - Ruff lint checks.
  - Ruff formatting checks.
  - ty type checks.
  - pytest.
- Ensure `devbox run init` creates the environment and installs the pre-commit hook.
- Add a minimal CLI behavior or remove the placeholder script entry if it has no justified use.
- Document any prerequisite that cannot be automated safely.

Acceptance criteria:

- Dependency lockfiles are current.
- `devbox run init` succeeds from a clean checkout.
- `devbox run check` succeeds.
- `pre-commit run --all-files` succeeds.
- No generated-project architecture is introduced.

Commit in small steps, separating dependency/tooling changes from behavior changes when practical.

## Phase 2: Copier questionnaire core

Goal: encode selection rules without generating component application source.

- Add `copier.yml` with a supported minimum Copier version and a dedicated template subdirectory.
- Add a required, non-empty `project_name` question.
- Add a top-level multi-select component question:
  - Frontend.
  - Client.
  - Backend.
  - Default to Frontend for non-interactive generation.
  - Reject an empty selection.
- Ask for `frontend_variant` only when Frontend is selected:
  - React, the default.
  - Astro.
- Ask for backend variants only when Backend is selected:
  - Hono.
  - FastAPI.
  - Allow both.
  - Reject an empty backend selection.
- Add component-scoped optional feature questions:
  - Frontend: Playwright, AI SDK, TanStack Query, and i18next.
  - Client: Playwright, AI SDK, TanStack Query, and i18next.
  - Hono: AI SDK.
  - FastAPI: PydanticAI.
- Keep frontend and client feature answers independent.
- Derive artifact descriptions from selections; do not prompt for artifact targets.

Acceptance criteria:

- Copier accepts every valid component combination.
- Copier rejects no-component and backend-with-no-variant answers with useful messages.
- Conditional questions are absent when their component is not selected.
- Default generation selects a React frontend and no optional integrations.

Commit the questionnaire separately from generated-file templates and tests where feasible.

## Phase 3: Shared generated files

Goal: render only files whose meaning is common to every valid generated project.

- Persist answers in `.copier-answers.yml` for future template updates.
- Generate a project README that summarizes:
  - Selected components and variants.
  - Enabled optional integrations.
  - Expected artifact for each selection.
- Generate a conservative `.gitignore` containing only entries justified by selected runtimes.
- Generate Devbox configuration containing shared security tools and only the runtimes needed by selected components.
- Generate a pre-commit configuration with Gitleaks.
- Avoid application source, package manifests, component directories, Dockerfiles, Wrangler configuration, Tauri configuration, and Compose files in this phase.

Acceptance criteria:

- Unselected runtimes and features leave no configuration residue.
- Answer persistence is stable enough for `copier update`.
- Generated documentation accurately reflects every tested selection.
- Rendering the same answers twice is deterministic.

## Phase 4: Render matrix and update tests

Goal: establish reliable coverage before adding component generators.

- Build pytest helpers around Copier's programmatic API.
- Render and inspect at least these cases:
  - Default React frontend.
  - Astro frontend.
  - Client only.
  - Hono only.
  - FastAPI only.
  - Hono and FastAPI together.
  - Frontend and client together, confirming independent answers.
  - All top-level components with all optional integrations.
- Test invalid selections and error messages.
- Test absence of files, dependencies, runtimes, and text associated with unselected components.
- Test deterministic rerendering and, once supported, a representative `copier update` path.
- Prefer structural assertions over large snapshots; use snapshots only where they improve reviewability.

Acceptance criteria:

- The complete render matrix passes through `devbox run check`.
- Tests demonstrate independent outputs without assuming shared source code.
- Tests do not lock in component layouts that have not been designed.

## Phase 5: Component generators

Implement each generator as its own milestone. Before coding a generator, document its output paths, build commands, artifact boundary, and component-local architecture. Each milestone includes its own render tests and must not require another component to be selected.

### 5.1 React frontend

- Design its component-local output layout.
- Add Bun, React, TypeScript, Tailwind CSS, shadcn/ui, Biome, and Testing Library.
- Render optional Playwright, AI SDK, TanStack Query, and i18next integrations independently.
- Provide a production build that emits provider-neutral static files.

### 5.2 Astro frontend

- Design its component-local output layout independently from React.
- Add Astro, Bun, TypeScript, and Biome.
- Preserve a provider-neutral static build by default.
- Only add server-side rendering configuration if a future explicit option requires it.

### 5.3 Tauri client

- Decide desktop/mobile targeting questions and prerequisites before implementation.
- Design an independent React UI and Tauri shell; do not import the selected frontend implicitly.
- Add client-scoped optional integrations.
- Validate the feasible build targets in CI and document platform-specific validation gaps.

### 5.4 Hono backend

- Design its component-local output layout.
- Add Bun, Hono, tests, and Cloudflare configuration.
- Add AI SDK only when selected.
- Validate the Cloudflare edge build artifact without deploying it.

### 5.5 FastAPI backend

- Design its component-local output layout.
- Add uv, Python, FastAPI, pytest, Ruff, and ty.
- Add PydanticAI only when selected.
- Add a production OCI container definition and validate that it builds without publishing or deploying it.

## Phase 6: Integration and maintenance

- Test representative multi-component generations without assuming component coupling.
- Add CI for repository checks and the render matrix.
- Pin or constrain tool versions and define an intentional update process.
- Test Copier upgrades against existing answer files.
- Document release/versioning policy for breaking questionnaire or output changes.
- Add deployment or orchestration features only after their contracts are explicitly designed and approved.

## Out of scope until separately designed

- A universal generated-project directory layout.
- Shared UI or source code between frontend and client.
- Docker Compose or cross-service orchestration.
- Remote deployment, image publication, or Cloudflare resource mutation.
- Resolving 1Password references into files or logs.
