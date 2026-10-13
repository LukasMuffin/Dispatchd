# dispatchd

dispatchd is a multi-tenant webhook delivery service written in Python. Tenants send
events to an HTTP ingest API, and a separate worker delivers them to each tenant's
registered endpoints, with retries, exponential backoff, a dead-letter queue,
idempotent ingestion, and HMAC-signed payloads. It's built with FastAPI and Postgres.
This repository is currently a project skeleton; see [CLAUDE.md](CLAUDE.md) for the
milestones and [docs/adr/](docs/adr/) for design decisions.

## Running locally

Requirements: [uv](https://docs.astral.sh/uv/) and Docker.

### With Docker Compose

```sh
docker compose up --build
curl http://localhost:8000/health   # {"status":"ok"}
```

This starts Postgres, the API on port 8000, and the worker.

### Without Docker

```sh
uv sync
uv run uvicorn dispatchd.api.app:app --reload   # API on http://localhost:8000
uv run dispatchd-worker                         # worker (Ctrl+C to stop)
```

Settings come from environment variables prefixed with `DISPATCHD_`, such as
`DISPATCHD_DATABASE_URL` and `DISPATCHD_LOG_LEVEL`. See
[src/dispatchd/core/config.py](src/dispatchd/core/config.py).

### Checks

```sh
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run pytest
```
