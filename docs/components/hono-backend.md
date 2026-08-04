# Hono backend generator

## Output boundary

- Path: `backend/hono/`
- Production artifact: Cloudflare Worker bundle in `backend/hono/dist/`
- Development command: `bun run --cwd backend/hono dev`
- Formatting command: `bun run --cwd backend/hono format`
- Validation commands: `bun run --cwd backend/hono check` and `bun run --cwd backend/hono test`
- Artifact command: `bun run --cwd backend/hono build`

## Local architecture

The service is an independent Hono application targeting the Cloudflare Workers
runtime. `wrangler deploy --dry-run` produces the edge artifact without remote
resource access. No deployment command is part of repository validation.
