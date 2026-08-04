# Repository Instructions

## Scope and source of truth

- Read `README.md` for the implemented component model and `PLAN.md` for current constraints and deferred design decisions before making architectural changes.
- Keep components independent. Do not invent a universal generated layout, shared UI package, Docker Compose setup, or service orchestration without an explicit design decision.
- Treat frontend, client, Hono, and FastAPI as separate generators with component-specific outputs.
- Do not implement deferred capabilities without an explicit design decision.

## Working method

- Inspect the working tree before editing and preserve unrelated or user-authored changes.
- Make small, reviewable commits. Each commit should represent one coherent change and leave the repository in a valid state.
- Prefer commits in this order when applicable: tooling, questionnaire, shared templates, tests, then one component generator at a time.
- Do not combine broad formatting, dependency upgrades, generated output, and behavioral changes in one commit.
- Run the narrowest relevant checks during development and the full repository check before completing a milestone.
- Use `devbox run check` as the primary local validation command once that script covers all repository checks.
- Template rendering and local artifact builds are validation. Commands that mutate remote resources are deployments and require explicit user authorization.

## Copier design rules

- Require at least one of Frontend, Client, or Backend.
- Use React as the non-interactive default frontend selection.
- Keep React and Astro mutually exclusive frontend variants.
- Allow Hono, FastAPI, or both when Backend is selected; reject an empty backend selection.
- Keep frontend and client optional integrations independently selectable.
- Keep optional integrations disabled by default.
- Derive fixed artifact types from component choices rather than asking users to select them.
- Avoid emitting configuration, dependencies, files, or documentation for unselected components.
- Preserve `.copier-answers.yml` compatibility and add update tests before changing existing question names or answer shapes.

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

- Treat `devbox run boot` and `devbox run comp` as deployment operations because they modify remote systems.
- Do not run deployment commands, publish artifacts, push images, or mutate Cloudflare or other remote resources unless the user explicitly asks for that operation.
- Do not interpret a request to test or validate as permission to deploy.

## Completion expectations

- Run `git diff --check` for edited files.
- Run relevant formatters, linters, type checks, and tests available for the changed scope.
- Report checks that could not be run and why.
- Confirm the staged diff before every commit so unrelated files are not included.
- Use descriptive commit messages and report the resulting commit hash.
