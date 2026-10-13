# CLAUDE.md

## Project

dispatchd is a multi-tenant webhook delivery service written in Python, built as a
portfolio project. Tenants submit events through an HTTP API, and dispatchd delivers
them reliably to the tenants' registered endpoints.

**Roles:** the project owner makes the design decisions. Claude implements them in
small, reviewable PRs.

### Milestones

1. Ingest API + delivery worker
2. Retries, backoff, dead-letter queue, idempotency
3. API keys + HMAC signing
4. Dashboard
5. Tests, deploy, load test

## Layout

- `src/dispatchd/api/`: FastAPI app (`dispatchd.api.app:app`)
- `src/dispatchd/worker/`: delivery worker (`dispatchd-worker` / `python -m dispatchd.worker`)
- `src/dispatchd/core/`: code shared by the API and the worker. `api/` and `worker/`
  must not import from each other.
- `tests/`: pytest suite
- `docs/adr/`: Architecture Decision Records

## Commands

```sh
uv sync                      # install deps
uv run ruff check .          # lint
uv run ruff format .         # format
uv run mypy                  # type check (strict)
uv run pytest                # tests
docker compose up --build    # run Postgres + API + worker
```

CI runs lint, format check, mypy, and pytest on every PR. All of them must pass.

## Conventions

- Keep PRs small, one concern per PR.
- Every change ships with tests.
- Use type hints everywhere. mypy runs in strict mode.
- Add dependencies with `uv add` (or `uv add --dev`), and commit `uv.lock`.

## Git and PR rules

- Never push directly to `main`, and never merge PRs. The project owner merges.
- Name branches `feat/...`, `fix/...`, or `docs/...`.
- Every PR description explains **what** changed, **why**, and **how it was tested**.

## Design decisions: stop and write an ADR

When a change requires a design decision (choosing a technology, a data model, an
API contract, a delivery guarantee, and so on), do not pick one and keep going:

1. Copy `docs/adr/template.md` to `docs/adr/NNN-short-title.md`, using the next number.
2. Set the status to **Proposed**, and lay out 2–3 options with their tradeoffs.
3. Stop and wait for the project owner's decision. Don't implement anything that
   depends on it until the ADR is marked **Accepted**.

### Open ADRs

- ADR-001 Queue backend: Proposed
