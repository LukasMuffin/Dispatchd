# ADR-002: Database access

- **Status:** Proposed
- **Date:** 2026-10-13

## Context

ADR-001 made Postgres the job queue as well as the store for tenants, endpoints, and
events. Both the API and the worker now need to talk to it, through shared code in
`dispatchd.core`. Three choices are tied together here:

- **Driver:** which library opens connections and sends queries.
- **Query layer:** hand-written SQL, SQLAlchemy Core (a Python query builder), or the
  SQLAlchemy ORM (mapped classes and a session).
- **Sync or async:** whether database calls block a thread or are awaited.

What matters for this project:

- **Queue queries need exact SQL.** Claiming work uses `SELECT ... FOR UPDATE SKIP
  LOCKED`, and the lease handling from ADR-001 depends on which statements run in
  which transaction. The layer must not hide or reorder that.
- **mypy runs in strict mode**, so the library needs real type hints.
- **Tests run against a real Postgres** (planned for the next implementation PR), so
  the test setup should be simple.
- **The worker is I/O bound.** Most of its time goes to waiting on tenants' HTTP
  endpoints, so how it runs many deliveries at once matters (worked out in a later
  ADR on worker semantics).
- **It's a portfolio project.** Code a reviewer can read and follow counts for more
  than squeezing out performance.

## Options

### Option A: psycopg 3 with hand-written SQL (sync)

Queries are SQL strings in a small repository module per table. psycopg's row
factories (`class_row`) turn result rows into dataclasses or Pydantic models.
Connections come from `psycopg_pool.ConnectionPool`.

- **Pros:**
  - Every query is visible exactly as Postgres runs it, which suits the queue code.
  - Few dependencies: `psycopg` and `psycopg-pool`.
  - The driver ships type hints and works under mypy strict.
  - psycopg 3 has both a sync and an async API with the same shape, so switching to
    async later only touches the call sites.
  - Server-side parameter binding, and `jsonb` maps to Python dicts out of the box.
- **Cons:**
  - More boilerplate: each query needs its own row type and mapping.
  - mypy can't check SQL strings. A typo in a column name shows up only when a test
    runs the query.
  - The schema lives in two places, the migration SQL and the Python row types, kept
    in sync by hand and by tests.
  - No migration autogeneration (relevant to the migrations ADR).

### Option B: SQLAlchemy 2.0 on psycopg 3 (sync), Core or ORM

Tables are declared in Python. With **Core**, queries are built with
`select(...).with_for_update(skip_locked=True)` and run on a connection. With the
**ORM**, tables are mapped classes (`Mapped[...]` attributes) loaded and saved
through a `Session`.

- **Pros:**
  - Typed table definitions (2.0 has native typing), and queries can be composed in
    Python.
  - Table metadata lets Alembic autogenerate migrations.
  - Widely used and familiar to reviewers.
  - Core keeps the SQL close to what you'd write by hand. The ORM removes most row
    mapping code.
- **Cons:**
  - A large dependency with a lot of concepts: engines, connections, sessions, unit
    of work, and lazy vs eager loading.
  - The ORM decides when to flush and what SQL to emit. For queue code, where the
    exact statements and transaction boundaries matter, that hides important
    behavior. Core avoids this, but then much of the ORM's convenience is gone.
  - Queries are written in a Python DSL, so a reader has to translate back to SQL
    to see what the queue does.
  - Async SQLAlchemy has its own pitfalls (implicit lazy loads fail under asyncio).

### Option C: asyncpg with hand-written SQL (async)

The API and worker are fully async. Queries are SQL strings, run on an
`asyncpg.Pool`.

- **Pros:**
  - The fastest Python Postgres driver.
  - Async from the start: one worker process can wait on many HTTP deliveries at
    once.
  - Every query is visible SQL, as with Option A.
- **Cons:**
  - Async only. Everything that touches the database becomes `async`, including
    tests (which need pytest-asyncio or anyio).
  - No type hints of its own. mypy strict needs the third-party `asyncpg-stubs`
    package.
  - Uses `$1`-style placeholders, and `json`/`jsonb` need a custom codec to come back
    as dicts.
  - Its speed advantage is unlikely to matter here: ADR-001 already puts the
    throughput ceiling on the queue's row locking, not on the driver.

## Sync or async

This is partly separate from the library choice: psycopg 3 and SQLAlchemy both offer
sync and async APIs, while asyncpg is async only.

- **API:** FastAPI runs plain `def` handlers in a thread pool, so sync database code
  doesn't block the server. At this project's scale, sync is fine for the API.
- **Worker:** the real question is how to run many deliveries at once. With sync
  code that means a thread pool or more worker processes. With async it means many
  tasks in one event loop. The worker semantics ADR decides the model, but this
  choice limits it.

Starting sync and moving to async later is cheapest with psycopg 3 (same driver,
parallel APIs). Starting async means paying the async cost in every layer up front.

## Comparison

| | A: psycopg 3 + SQL | B: SQLAlchemy 2.0 | C: asyncpg + SQL |
|---|---|---|---|
| SQL visible in code | Yes | Core: mostly; ORM: no | Yes |
| Typed under mypy strict | Yes (built in) | Yes (built in) | Third-party stubs |
| Sync / async | Both | Both | Async only |
| Row → object mapping | Row factories, by hand | Automatic (ORM) | By hand |
| Migration autogeneration | No | Yes (Alembic) | No |
| Dependency size | Small | Large | Small |
| Raw driver speed | Good | Good (psycopg underneath) | Best |

## Questions that would decide this

- Is visible, hand-written SQL a feature for this portfolio, or is a typed query
  layer worth more?
- Should the worker run deliveries concurrently with async from the start, or with
  threads/processes in sync code?
- Do you want migrations autogenerated from Python models (only Option B allows
  this), or written by hand?

## Decision

_Pending. The project owner will decide._

## Consequences

_To be written once a decision is made._
