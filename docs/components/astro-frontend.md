# Astro frontend generator

## Output boundary

- Path: `frontend/`
- Production artifact: provider-neutral static files in `frontend/dist/`
- Development command: `bun run --cwd frontend dev`
- Validation commands: `bun run --cwd frontend check` and `bun run --cwd frontend build`

## Local architecture

The frontend is an independent, statically generated Astro site. Pages live in
`frontend/src/pages`, while optional component-local integrations live in
`frontend/src/integrations`. It has no server adapter and imports no React
frontend or Tauri client source.
