FROM ghcr.io/astral-sh/uv:0.12.1 AS uv
FROM python:3.14-slim

COPY --from=uv /uv /uvx /bin/

WORKDIR /app
COPY pyproject.toml ./
RUN uv sync --no-dev

COPY app ./app

EXPOSE 8000
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
