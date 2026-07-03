# Design Decisions & Trade-offs

Building a distributed job scheduler involves balancing reliability, complexity, latency, and operational overhead. Below are the major architectural trade-offs made in this project.

## 1. PostgreSQL `SKIP LOCKED` vs External Message Broker (Redis/RabbitMQ)

**Decision**: Use PostgreSQL as the job queue via `SELECT ... FOR UPDATE SKIP LOCKED`.

**Trade-offs**:
- *Pros*: Eliminates the need for a separate infrastructure component (Redis/RabbitMQ). Simplifies deployment, backup, and transaction management. Jobs and business data (Users, Projects) live in the same ACID-compliant datastore, making atomic operations trivial (e.g., delete queue cascades to delete jobs).
- *Cons*: Higher latency than an in-memory datastore like Redis. Heavy polling can strain the database CPU.
- *Rationale*: For this assignment, emphasizing reliability, atomic transactions, and relational database design was prioritized over absolute microsecond latency. `SKIP LOCKED` scales surprisingly well for many typical background processing workloads.

## 2. Polling vs WebSockets for Dashboard Live Updates

**Decision**: Aggressive polling via React Query (every 5-10 seconds) instead of WebSockets.

**Trade-offs**:
- *Pros*: Vastly simplifies the backend. WebSockets require connection state management, load balancer configuration, and complex broadcast logic (often necessitating Redis Pub/Sub in a multi-instance API deployment). Polling is stateless and scales horizontally out of the box.
- *Cons*: Slight delay in UI updates. Incurs higher HTTP request volume.
- *Rationale*: React Query makes polling trivial to implement and handles caching/deduplication. For a dashboard monitoring system health, a 5-second delay is acceptable and removes a massive layer of infrastructure complexity.

## 3. Custom `CronScheduler` vs external cron daemon (Celery Beat)

**Decision**: Embed an `asyncio` task loop (`CronScheduler`) directly into the FastAPI application lifespan.

**Trade-offs**:
- *Pros*: No need to run and monitor a separate scheduling process.
- *Cons*: If running multiple API instances, they might race to dispatch the same cron job.
- *Mitigation*: We solved the race condition by using `SELECT ... FOR UPDATE SKIP LOCKED` inside the `CronScheduler` itself when querying the `ScheduledJobs` table, ensuring only one API instance can dispatch a specific due job.

## 4. Separation of Job and Execution History

**Decision**: Separate `Jobs` table from `JobExecutions` and `JobLogs` tables.

**Trade-offs**:
- *Pros*: Keeps the core `Jobs` table narrow and fast to query during polling. Retries generate new `JobExecution` records rather than overwriting historical error data.
- *Cons*: Requires joining tables or making multiple queries to see the full context of a job.
- *Rationale*: Observability was a key requirement. Keeping a strict log of every execution attempt and its stack trace is vital for debugging in a distributed system, outweighing the minor query overhead.

## 5. Async SQLAlchemy

**Decision**: Use `asyncpg` and `AsyncSession` throughout the backend.

**Trade-offs**:
- *Pros*: High concurrency. A single API process can handle thousands of concurrent polling requests without exhausting OS threads.
- *Cons*: Adds complexity; `Lazy loading` of relationships is generally unsupported in async SQLAlchemy without special configuration.
- *Rationale*: FastAPI is built for async. To maximize throughput on I/O bound database queries (like dashboard metrics), async DB drivers are the optimal choice.

## 6. `RetryPromoter` Background Task

**Decision**: Add a second background asyncio loop (`RetryPromoter`) to re-queue delayed-retry jobs.

**Problem**: When a job fails and is given a retry delay (`status=scheduled`, `scheduled_at=future`), the worker's `claim_next_job` only queries `status=queued` jobs. Without promotion, retried jobs stay stuck in `scheduled` state forever.

**Trade-offs**:
- *Pros*: Clean separation of concerns — the worker's claiming logic remains simple (just `status=queued`). The promoter handles the scheduled→queued transition atomically.
- *Cons*: Adds a second background task to the process. Could be merged into the CronScheduler to reduce loop count.
- *Alternative considered*: Modifying `claim_next_job` to also select `status=scheduled AND scheduled_at <= NOW()`. Rejected because it complicates the core claiming query and mixes two concerns.
- *Mitigation*: `SKIP LOCKED` prevents race conditions across multiple promoter instances.

## 7. Dual-Level Job Priority

**Decision**: Priority is supported at both the Queue level and the Job level.

**Implementation**: Worker's `claim_next_job` sorts by `Job.priority DESC, Queue.priority DESC, Job.created_at ASC`.

**Trade-offs**:
- *Pros*: Fine-grained control. Urgent one-off jobs can jump ahead within their queue without changing the entire queue's priority. Queue-level priority lets operators triage a whole category of work.
- *Cons*: Slightly more complex ordering logic.
- *Rationale*: Production systems often need to expedite a specific job (e.g., "process this user's request immediately") without affecting the global queue ordering. Job-level priority enables this cleanly.

## 8. RBAC — Lightweight Role Model

**Decision**: Implement a two-tier RBAC model: `admin` and `member` roles at the user level, with org-scoped resource visibility.

**Trade-offs**:
- *Pros*: Simple to understand and implement. `admin` users bypass all org-scoping and see all data. `member` users only see their own org's projects.
- *Cons*: Coarse-grained. A real production system might need per-project roles (viewer, editor, owner) or per-queue roles.
- *Rationale*: The `require_role()` dependency factory (in `deps.py`) makes it easy to add more granular roles later. The org-scoping pattern in `list_projects` shows the approach that would be extended to queues and jobs in a production hardening pass.

## 9. Rate Limiting via `slowapi`

**Decision**: Add 100 requests/minute per IP rate limiting using `slowapi` (ASGI middleware wrapping `limits`).

**Trade-offs**:
- *Pros*: Protects against API abuse and denial-of-service. Zero-config — works with any ASGI server. The limit (100/min) is generous for legitimate dashboard usage but blocks scrapers.
- *Cons*: IP-based limiting breaks behind NATs or load balancers. In production, you'd use a Redis-backed limiter with user-ID keys for better accuracy.
- *Rationale*: Adding even basic rate limiting demonstrates security awareness. The `slowapi` library integrates cleanly with FastAPI's middleware pattern.

## 10. `passlib.CryptContext` vs Raw `bcrypt`

**Decision**: Standardize on `passlib.CryptContext(schemes=["bcrypt"])` rather than importing `bcrypt` directly.

**Trade-offs**:
- *Pros*: `passlib` provides a consistent API for password hashing that abstracts the underlying library. If we want to switch to Argon2 in the future, we change one line. Also handles `$2b$` vs `$2a$` bcrypt variants transparently.
- *Cons*: One extra abstraction layer.
- *Rationale*: The project already depends on `passlib[bcrypt]`. Importing raw `bcrypt` directly creates a dependency on transitive installation behavior, which is fragile.
