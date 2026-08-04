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

## Cloudflare deployment

`backend/hono/infrastructure/` contains a reusable Worker module and independent
staging and production roots. OpenTofu owns only the Worker resource. Wrangler
uploads immutable application versions and deploys the commit-tagged version, so
application bundles are not stored in OpenTofu state.

Each root declares a partial S3 backend for an environment-specific Cloudflare R2
bucket. Generated checks use `tofu init -backend=false` and cannot deploy. The
dedicated Cloudflare workflow supplies backend and account values from the matching
GitHub environment, applies infrastructure, builds locally, and then releases.
