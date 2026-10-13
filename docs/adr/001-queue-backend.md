# ADR-001: Queue backend

- **Status:** Proposed
- **Date:** 2026-10-12

## Context

The API accepts events from tenants. The worker has to deliver each event to the
tenant's endpoints. Something needs to sit between them and hold pending deliveries.

Requirements from the milestones:

- **Durability:** an accepted event must never be lost, even if a worker crashes mid-delivery.
- **Delayed retries** with backoff that can grow from seconds to hours (milestone 2).
- **Dead-letter queue:** a place for deliveries that have run out of retries, where
  they can be inspected and replayed (milestones 2 and 4).
- **Idempotency:** a duplicate ingest must not lead to a duplicate delivery (milestone 2).
- **Tenant fairness:** one noisy tenant shouldn't starve the others.
- **Visibility:** the dashboard (milestone 4) needs to show delivery state and history.
- **Easy local setup:** `docker compose up` should be all it takes. Postgres is
  already part of the stack.

Delivery semantics will be at-least-once whichever option we pick. Receivers dedupe
using an event ID.

## Options

### Option A: Postgres with `SELECT ... FOR UPDATE SKIP LOCKED`

Deliveries are rows in a table with columns such as `status`, `next_attempt_at`, and
`attempts`. Workers claim a batch with `SKIP LOCKED`, so several workers can poll at
once without blocking each other or claiming the same row.

- **Pros:**
  - No new infrastructure, since Postgres is already in the stack.
  - Enqueueing happens in the same transaction as storing the event, so there's no
    dual-write problem and no need for an outbox.
  - Delayed retries are just `next_attempt_at > now()`. The DLQ is a status value.
    Idempotency is a unique constraint.
  - The dashboard can query the queue directly with SQL, and fairness rules can be
    written in SQL too (for example, round-robin by tenant).
- **Cons:**
  - Polling adds latency and load. `LISTEN/NOTIFY` can reduce that, at the cost of
    some complexity.
  - Throughput tops out somewhere in the low thousands of jobs per second on a
    single primary. That's plenty for this project but not unlimited.
  - Frequent updates churn the table, so autovacuum needs attention under load.
  - Holding a row lock for the length of an HTTP call ties up connections. The fix
    is a lease column (claim, commit, deliver, update), which we'd have to build
    and test ourselves.

### Option B: Redis Streams

Events are added to a stream with `XADD`. Workers read through a consumer group
with `XREADGROUP` and acknowledge with `XACK`. `XAUTOCLAIM` reclaims messages from
consumers that crashed.

- **Pros:**
  - Low latency through blocking reads, with no polling.
  - High throughput.
  - Consumer groups and pending-entry tracking are built in.
- **Cons:**
  - Adds a second stateful service to run, back up, and configure. Durability
    depends on AOF/fsync settings.
  - Event records stay in Postgres, so every enqueue writes to two systems. We'd
    need an outbox or have to accept that some events could be lost or orphaned.
  - Streams have no built-in delays. Backoff needs a separate sorted set and a
    process that moves due jobs back into the stream.
  - The DLQ, idempotency, and fairness all have to be built by hand. Streams are
    hard to query, so the dashboard would still read state from Postgres.
  - Everything is held in memory, so a backlog during an outage costs RAM.

### Option C: Managed queue (AWS SQS, GCP Pub/Sub)

A cloud provider runs the queue. Using SQS as the example: visibility timeouts
handle crashed workers, and a redrive policy handles dead letters.

- **Pros:**
  - No queue to operate, and it scales without any work on our side.
  - Visibility timeouts, a redrive-based DLQ, and retention are built in.
  - It's a well-known production pattern that reviewers will recognize.
- **Cons:**
  - Same dual-write problem as Option B.
  - Ties the project to one vendor and costs money. Local development needs an
    emulator (LocalStack or the Pub/Sub emulator), and CI needs one too.
  - SQS delays max out at 15 minutes, so longer backoff means re-enqueueing or a
    scheduler in Postgres.
  - Standard SQS doesn't guarantee ordering. FIFO queues limit throughput, and
    per-tenant fairness is hard to control.
  - You can't query what's in the queue, so the dashboard again needs Postgres.
  - A portfolio reviewer sees less of our own engineering.

## Comparison

| | Postgres SKIP LOCKED | Redis Streams | Managed queue |
|---|---|---|---|
| New infrastructure | None | Redis | Cloud account + emulator |
| Atomic with event write | Yes | No (outbox needed) | No (outbox needed) |
| Delayed retries | Native (`next_attempt_at`) | Custom (sorted set) | ≤15 min on SQS, then custom |
| DLQ / replay | Status value + SQL | Custom | Built in (redrive) |
| Dashboard queries | Direct SQL | Need Postgres mirror | Need Postgres mirror |
| Throughput ceiling | Lower (~10³/s) | High | Very high |
| Latency | Poll interval, or NOTIFY | Low (blocking read) | Low–medium |
| Local dev / CI | Already there | One more container | Emulator |

## Questions that would decide this

- Is a throughput target above roughly 1k deliveries/sec part of the load-test
  goal (milestone 5)?
- Is "no extra infrastructure, and transactional enqueue" worth more than showing
  experience with a dedicated broker?
- Is deploying to a specific cloud (milestone 5) a goal, which would make Option C
  cheap to adopt?

## Decision

_Pending. The project owner will decide._

## Consequences

_To be written once a decision is made._
