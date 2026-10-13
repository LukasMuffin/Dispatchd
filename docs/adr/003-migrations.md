# ADR-003: Database migrations

- **Status:** Proposed
- **Date:** 2026-10-13

## Context

Milestone 1 creates the first tables (tenants, endpoints, events, deliveries), and
every later milestone changes them: retry columns and idempotency keys (milestone 2),
API keys (milestone 3), and indexes for the dashboard (milestone 4). Schema changes
need to be versioned, applied in order, and repeatable on a laptop, in CI, and in
the milestone 5 deploy.

Two things to decide:

1. **The tool:** what writes, tracks, and applies migrations.
2. **When migrations run:** what applies them under `docker compose up` (and later
   in deploys), so the API and worker never start against an old schema.

This depends on ADR-002. The comparison below notes where an option fits better or
worse with each ADR-002 outcome.

What matters:

- `docker compose up` stays the only setup step.
- Tests run against a real Postgres, so the test suite must be able to apply the
  schema to a fresh database quickly.
- Queue tables (ADR-001) rely on partial indexes and other Postgres-specific
  features, so migrations must be able to express arbitrary SQL.
- Two processes (API and worker, and later several replicas) must not race to apply
  the same migration.

## Options: the tool

### Option A: Alembic

The standard migration tool for SQLAlchemy. Each migration is a Python file with
`upgrade()` and `downgrade()` functions, and Alembic tracks the current version in
an `alembic_version` table.

- **Pros:**
  - Widely used and well documented, and reviewers will recognize it.
  - With SQLAlchemy table metadata (ADR-002 Option B), `alembic revision
    --autogenerate` drafts migrations from model changes.
  - Supports downgrades and branching/merging of migration heads.
  - Raw SQL is always available through `op.execute(...)`.
- **Cons:**
  - Depends on SQLAlchemy. If ADR-002 picks A or C, we'd add SQLAlchemy just to run
    migrations.
  - Without SQLAlchemy models there is no autogeneration, so most of its advantage
    over plain SQL files disappears.
  - Migrations are Python wrapping SQL, which is one more layer to read.
  - Concurrent runs aren't locked by default. We'd add an advisory lock in `env.py`
    or run migrations from only one place.

### Option B: Plain `.sql` files with our own small runner

Migrations are numbered files (`001_initial.sql`, `002_...sql`) in
`src/dispatchd/core/migrations/`. A short runner in `dispatchd.core` (a
`dispatchd-migrate` command) takes a Postgres advisory lock, applies pending files
in order, each in its own transaction, and records them in a `schema_migrations`
table. Migrations are forward-only.

- **Pros:**
  - Migrations are plain SQL, so they read the same as the SQL in the app (fits
    ADR-002 A or C).
  - No new dependency. The runner uses the same driver as the app.
  - We control locking, logging, and how tests apply the schema.
  - A small piece of infrastructure we wrote and tested ourselves, which reviewers
    can see.
- **Cons:**
  - We have to build and test it ourselves (on the order of 50–100 lines plus
    tests), and maintain it.
  - No downgrades. Undoing a change means writing a new forward migration.
  - No autogeneration.
  - Edge cases a mature tool already handles are ours to get right, for example
    statements that can't run in a transaction (`CREATE INDEX CONCURRENTLY`).

### Option C: dbmate

A standalone migration tool written in Go. Each migration is one `.sql` file with
`-- migrate:up` and `-- migrate:down` sections, tracked in a `schema_migrations`
table. It ships as a single binary and as a Docker image.

- **Pros:**
  - Plain SQL migrations with up and down sections, without writing our own runner.
  - Language-agnostic and independent of the ADR-002 choice.
  - Can wait for the database to accept connections (`--wait`), which suits a
    compose service.
- **Cons:**
  - Not a Python package, so `uv sync` can't install it. Developers and CI need the
    binary separately (Homebrew, a release download, or its Docker image).
  - Tests have to call an external binary to set up the schema.
  - By default it also writes a `schema.sql` dump, which needs `pg_dump` and means
    one more file to keep in the repo (or turn off).
  - Less familiar to Python reviewers than Alembic.

## Options: when migrations run

### Option 1: A one-off `migrate` service in docker compose

A `migrate` service runs the migrations and exits. `api` and `worker` declare
`depends_on: migrate: condition: service_completed_successfully`.

- **Pros:** migrations run once, before anything else starts. The same pattern
  carries over to a deploy (a release step or a Kubernetes Job). The API and worker
  don't need permission to change the schema.
- **Cons:** one more service in `docker-compose.yml`, and running the API outside
  compose means remembering to migrate first.

### Option 2: The API applies migrations on startup

- **Pros:** nothing extra to run. Starting the API is enough.
- **Cons:** the worker can start before the API has migrated. Several API replicas
  race (an advisory lock solves this, but every replica still tries). Schema
  changes are tied to application startup, which makes a failed migration harder
  to separate from a failed deploy.

Whichever tool is picked, tests apply migrations to a fresh test database at the
start of the test session, so the tests exercise the same migrations as production.

## Comparison

| | A: Alembic | B: Own SQL runner | C: dbmate |
|---|---|---|---|
| Migration format | Python (`op.*` or `op.execute`) | Plain SQL | Plain SQL (up/down) |
| Autogeneration | Yes, with SQLAlchemy models | No | No |
| Downgrades | Yes | No (forward-only) | Yes |
| New dependency | Alembic + SQLAlchemy | None | Go binary, outside `uv` |
| Best fit with ADR-002 | Option B | Options A, C | Any |
| Concurrency lock | Add ourselves | Built into runner | Unverified; run from one place |
| Code we maintain | `env.py` config | The runner and its tests | None |

## Questions that would decide this

- If ADR-002 picks SQLAlchemy, is autogeneration worth having? If so, Alembic is
  the natural choice.
- If ADR-002 picks hand-written SQL, would you rather write a small runner (Option
  B) or depend on an external tool (Option C)?
- Do you want downgrade migrations, or is forward-only acceptable?

## Decision

_Pending. The project owner will decide._

## Consequences

_To be written once a decision is made._
