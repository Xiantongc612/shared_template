# FastAPI backend generator

## Output boundary

- Path: `backend/fastapi/`
- Production artifact: OCI-compatible container image built from `backend/fastapi/Dockerfile`
- Development command: `uv run --project backend/fastapi uvicorn app.main:app --reload`
- Formatting command: Ruff through the component's uv environment
- Validation commands: Ruff and ty, with pytest run separately
- Artifact command: `docker buildx build --output type=oci,dest=backend/fastapi/dist/fastapi-backend.tar backend/fastapi`

## Local architecture

The service is an independent Python package. Runtime code lives in
`backend/fastapi/app`, tests live in `backend/fastapi/tests`, and the container
definition installs only runtime dependencies. It shares no source or process
orchestration with Hono or other selected components.
