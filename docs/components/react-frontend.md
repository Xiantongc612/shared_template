# React frontend generator

## Output boundary

- Path: `frontend/`
- Production artifact: provider-neutral static files in `frontend/dist/`
- Development command: `bun run --cwd frontend dev`
- Validation commands: `bun run --cwd frontend check`, `bun test --cwd frontend`, and `bun run --cwd frontend build`

## Local architecture

The frontend is an independent Vite application. Application code lives in
`frontend/src`, shadcn/ui components live in `frontend/src/components/ui`, and
component-local integrations live in `frontend/src/integrations`. It does not
import source code from the optional Tauri client.

Tailwind CSS is compiled through Vite. The production build is static and has
no provider-specific adapter or deployment configuration.
