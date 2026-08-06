# shared_template

An opinionated [Copier](https://copier.readthedocs.io/) template for composing applications from independently selectable frontend, client, and backend components.

## Local development

This repository uses Devbox to manage development runtimes and utilities. Install
[Git](https://git-scm.com/) and [Devbox](https://www.jetify.com/devbox/docs/installing_devbox/),
then run `devbox run init` to create the Python environment and install the
pre-commit hook. Run `devbox run fmt` to format Python sources, `devbox run check`
for repository validation, `devbox run test` for the unit test suite, and
`devbox run build` to package the template archive. The pre-commit hook covers
the same fast checks as `check`. Dependency updates, Copier compatibility, and
release policy are documented in [`docs/maintenance.md`](docs/maintenance.md).

Run `devbox run integration` on Linux to render minimal and optional-integration
variants of every component independently. The suite executes generated checks,
tests, applicable Playwright tests, builds, and semantic artifact validation.
FastAPI cases require Docker Buildx, Tauri cases require the Linux system
libraries listed in the generated build workflow, and local Playwright setup may
require host browser libraries. Focused commands such as `devbox run
integration:react` and `devbox run integration:react-integrations` validate one
case.

## Component selection rules

- A generated project must include at least one frontend, client, or backend component.
- Components are independently selectable and may be combined in one generated project.
- The frontend has two mutually exclusive variants: React for application-style static sites and Astro for content-oriented static sites.
- The backend may include Hono, FastAPI, or both.
- When multiple components are selected, each produces an independent output. Selecting both a frontend and a client does not imply shared source code or a shared UI package.
- Optional integrations are opt-in unless a component lists them as part of its core stack.
- Each component has a fixed artifact type; artifact targets are not questionnaire options.

This template does not generate cross-component UI sharing, Docker Compose
configuration, or service orchestration. Those capabilities require separate
design decisions documented in `PLAN.md`.

## Shared tooling

- Devbox for development runtimes and utilities
- Gitleaks for secret scanning
- Semgrep for static application security testing with vendored rules
- actionlint for semantic validation of root and generated GitHub workflows
- pre-commit for Git hook management
- Generated root commands for formatting, static checks, unit tests, optional
  end-to-end tests, and local artifact builds
- Generated GitHub Actions with immutable action pins, bounded jobs, safe
  dependency caches with prefix-restore fallbacks, and a read-only validate
  stage that never builds or deploys for pull requests. The release stage builds
  artifacts and requires manual approval to publish, and the deploy stage
  consumes the released artifacts under a separate production approval boundary.
- Component-owned OpenTofu and Cloudflare release automation for Hono and Astro

## Frontend

The frontend produces provider-neutral static-site artifacts.

### React variant

- Bun as package manager, runtime, and test runner
- React and TypeScript
- Tailwind CSS and shadcn/ui
- Biome for linting and formatting
- Testing Library for React (`@testing-library/react`) for component tests

### Astro variant

- Astro for a content-oriented static site
- Bun as package manager and runtime
- TypeScript
- Biome for linting and formatting
- Static Cloudflare Pages projects for isolated staging and production releases

### Optional frontend integrations

- Playwright for end-to-end tests
- AI SDK (`ai`) for AI integration
- TanStack Query for server-state synchronization in the React variant
- i18next for internationalization

## Client

The client produces Tauri desktop application bundles. Generated GitHub automation
builds Linux AppImage and Debian artifacts; macOS, Windows, and mobile targets are
deferred. It uses an independent React frontend with the same core frontend
technologies where applicable. A validated `client_identifier` answer supplies
the stable reverse-domain Tauri application identity.

Optional client integrations are selected independently from frontend integrations.

## Backend

Both backend variants may be selected together.

### Hono edge service

The Hono backend produces a Cloudflare edge-function artifact.

- Bun as package manager, runtime, and test runner
- Hono as the web framework
- AI SDK (`ai`) as an optional AI integration
- OpenTofu-owned staging and production Workers released with Wrangler versions

### FastAPI service

The FastAPI backend produces an OCI-compatible container artifact.

- uv as package manager
- Python as runtime
- FastAPI as the web framework
- pytest as the test framework
- Ruff as the linter and formatter
- ty as the type checker
- PydanticAI as an optional AI integration
- Digest-pinned multi-platform uv and Python base images
