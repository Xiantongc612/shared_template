# FastAPI backend generator

## Output boundary

- Path: `backend/fastapi/`
- Production artifact: OCI-compatible container image built from `backend/fastapi/Dockerfile`
- Development command: `uv run --project backend/fastapi uvicorn app.main:app --reload`
- Validation commands: Ruff, ty, and pytest through the component's uv environment
- Artifact command: `docker build backend/fastapi`

## Local architecture

The service is an independent Python package. Runtime code lives in
`backend/fastapi/app`, tests live in `backend/fastapi/tests`, and the container
definition installs only runtime dependencies. It shares no source or process
orchestration with Hono or other selected components.
