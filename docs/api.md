# REST API Reference

All endpoints are prefixed with `/api/v1` and require a Bearer token in the `Authorization` header, except for `/auth/login` and `/auth/register`.

Rate limit: **100 requests per minute** per IP address.

## Authentication

### `POST /auth/register`
Create a new user.
- **Body**: `{"email": "user@example.com", "password": "password123"}`
- **Response**: `200 OK` `UserResponse` object

### `POST /auth/login`
Get a JWT access token.
- **Body** (Form Data): `username=user@example.com&password=password123`
- **Response**: `200 OK` `{"access_token": "...", "token_type": "bearer"}`

---

## Jobs

### `POST /jobs/`
Enqueue a single job.
- **Body**: 
  ```json
  {
    "queue_id": "uuid",
    "payload": {"task": "send_email", "to": "user@test.com"},
    "scheduled_at": "2026-07-01T12:00:00Z",
    "priority": 0
  }
  ```
  - `scheduled_at` (optional): If set, job is delayed until this time.
  - `priority` (optional, default 0): Higher values are executed first.
- **Response**: `201 Created`

### `POST /jobs/batch`
Enqueue multiple jobs atomically. Maximum 500 per batch.
- **Body**: `{"jobs": [{ "queue_id": "...", "payload": {...}, "priority": 5 }]}`
- **Response**: `201 Created` Array of Job objects

### `GET /jobs/`
List jobs with optional pagination and status filtering.
- **Query Params**: `skip=0`, `limit=100`, `status=queued|claimed|running|completed|failed|dlq|scheduled`
- **Response**: `200 OK` Array of Job objects

### `GET /jobs/{job_id}`
Get job details including current status, retry count, and priority.

### `GET /jobs/{job_id}/logs`
Get all log messages emitted during the job's lifecycle.
- **Response**: `200 OK` Array of `JobLogResponse` objects (id, message, timestamp)

### `GET /jobs/{job_id}/executions`
Get historical execution attempts, including error stack traces and worker assignments.
- **Response**: `200 OK` Array of `JobExecutionResponse` objects

### `POST /jobs/{job_id}/retry`
Manually retry a failed or DLQ job.
- **Response**: `200 OK` The updated job (status reset to `queued`, retry counter reset to 0).
- **Error**: `400` if job is not in `failed` or `dlq` state.

---

## Queues

### `POST /queues/`
Create a new queue with optional retry policy.
- **Body**:
  ```json
  {
    "project_id": "uuid",
    "name": "email-queue",
    "priority": 1,
    "concurrency_limit": 10,
    "retry_policy": {
      "max_retries": 3,
      "strategy": "exponential_backoff",
      "delay_seconds": 60,
      "backoff_multiplier": 2.0
    }
  }
  ```
  - `strategy`: one of `fixed_delay`, `linear_backoff`, `exponential_backoff`
- **Response**: `201 Created`

### `GET /queues/`
List all queues.

### `GET /queues/project/{project_id}`
List queues belonging to a specific project.

### `GET /queues/{queue_id}/stats`
Get live statistics for a queue (counts of jobs in each state).
- **Response**: `200 OK` `{"queued": 5, "running": 2, "completed": 100, "failed": 1, "dlq": 0, "scheduled": 3, "total": 111}`

### `PATCH /queues/{queue_id}`
Update queue configuration.
- **Body**: `{"is_paused": true}` (or name, priority, concurrency_limit)
- **Response**: `200 OK`

### `DELETE /queues/{queue_id}`
Delete a queue and all its associated jobs (CASCADE).
- **Response**: `204 No Content`

---

## Scheduled (Recurring) Jobs

### `POST /scheduled-jobs/`
Create a new recurring cron job. The scheduler dispatches a new `queued` Job on each cron tick.
- **Body**:
  ```json
  {
    "queue_id": "uuid",
    "name": "Daily Cleanup",
    "cron_expression": "0 0 * * *",
    "payload": {"task": "cleanup_expired_sessions"}
  }
  ```
  - `cron_expression`: Standard 5-field cron (minute hour day month weekday)
  - `name` (optional): Human-readable label
- **Response**: `201 Created` with `next_run_at` computed from expression
- **Error**: `422` if cron expression is invalid

### `GET /scheduled-jobs/`
List all recurring job definitions.
- **Query Params**: `skip=0`, `limit=100`, `active_only=false`
- **Response**: `200 OK` Array including `next_run_at`, `last_run_at`, `is_active`

### `GET /scheduled-jobs/{id}`
Get a specific recurring job definition.

### `PATCH /scheduled-jobs/{id}`
Update a recurring job (pause, change expression, update payload).
- **Body**: `{"is_active": false}` to pause, or change `name`, `cron_expression`, `payload`
- If `cron_expression` changes, `next_run_at` is recalculated automatically.
- **Response**: `200 OK`

### `DELETE /scheduled-jobs/{id}`
Remove a recurring job definition. Previously dispatched Jobs are not affected.
- **Response**: `204 No Content`

---

## Workers

### `GET /workers/`
List all registered workers with status, concurrency limit, heartbeat, and staleness flag.
- **Response**: Array of worker objects with `is_stale` (true if heartbeat > 2 min ago)

### `GET /workers/{worker_id}`
Get details for a specific worker.

### `POST /workers/{worker_id}/heartbeat`
Update a worker's heartbeat timestamp via REST (alternative to direct DB write).
- **Response**: `{"status": "ok", "heartbeat_at": "..."}`

---

## Metrics

### `GET /metrics/dashboard`
Returns high-level system metrics: active workers, queued/running jobs, failure rate, DLQ count, avg execution time.

### `GET /metrics/throughput`
Returns hourly job completion counts for the last 24 hours (for time-series charts).

### `GET /metrics/workers`
*(Deprecated — use `GET /workers/` instead)* Returns worker list.

---

## Projects

### `POST /projects/`
Create a new project. Auto-creates an organization if user has none.

### `GET /projects/`
List projects. Non-admin users see only their own organizations' projects (RBAC).

### `GET /projects/{project_id}`
Get a specific project.

---

## Error Format

All errors follow:
```json
{
  "detail": "Human-readable error message"
}
```

Common HTTP status codes:
- `400` Bad Request (validation, business rule violations)
- `401` Unauthorized (missing/invalid JWT)
- `403` Forbidden (RBAC — insufficient role)
- `404` Not Found
- `422` Unprocessable Entity (request body validation)
- `429` Too Many Requests (rate limit exceeded — 100 req/min)
