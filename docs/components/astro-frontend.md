# Astro frontend generator

## Output boundary

- Path: `frontend/`
- Production artifact: provider-neutral static files in `frontend/dist/`
- Development command: `bun run --cwd frontend dev`
- Formatting command: `bun run --cwd frontend format`
- Validation command: `bun run --cwd frontend check`
- Artifact command: `bun run --cwd frontend build`

## Local architecture

The frontend is an independent, statically generated Astro site. Pages live in
`frontend/src/pages`, while optional component-local integrations live in
`frontend/src/integrations`. It has no server adapter and imports no React
frontend or Tauri client source.

No unit-test framework is configured, so an Astro-only root test command succeeds
with a clear no-tests message. Optional Playwright coverage remains a separate
end-to-end concern.
