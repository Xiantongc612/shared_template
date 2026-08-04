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

## Cloudflare deployment

`frontend/infrastructure/` contains a reusable Pages module and independent
staging and production roots. OpenTofu owns each Pages project, and Wrangler
uploads the existing `frontend/dist/` static artifact after infrastructure is
applied. The generator does not add a Cloudflare adapter, Pages Functions, or SSR.

Each root declares a partial S3 backend for an environment-specific Cloudflare R2
bucket. Generated checks use `tofu init -backend=false`; only the dedicated
Cloudflare workflow supplies credentials, applies infrastructure, and uploads the
site.
