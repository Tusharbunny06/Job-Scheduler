# Architecture

The Codity Job Scheduler uses a robust, scalable architecture separated into distinct logical components.

## High Level Architecture

```mermaid
graph TD
    UI[Frontend (React/Vite)] --> |REST API| API[FastAPI Backend]
    
    API --> |CRUD & Scheduling| DB[(PostgreSQL)]
    
    subgraph Background Services
        Worker[Worker Process] --> |Polls Queue| DB
        Worker --> |Executes Jobs| Worker
        Worker --> |Heartbeat| DB
        
        Scheduler[Scheduler Daemon] --> |Cron Jobs| DB
        Scheduler --> |Retry Promotion| DB
        Scheduler --> |Stale Job Reclaimer| DB
    end
```

## Atomic Claiming Sequence

To ensure reliability and prevent duplicate execution across multiple workers, we use `SELECT ... FOR UPDATE SKIP LOCKED`.

```mermaid
sequenceDiagram
    participant W as Worker Node
    participant DB as Database
    
    W->>DB: poll_queues()
    DB-->>W: Wait if queue empty
    W->>DB: SELECT FOR UPDATE SKIP LOCKED
    Note over DB: Locks row so no other worker claims it
    DB-->>W: Returns Job ID 123
    W->>DB: UPDATE Job SET status = 'claimed'
    W->>W: Process Job Payload
    alt Success
        W->>DB: UPDATE Job SET status = 'completed'
    else Failure
        W->>DB: UPDATE Job SET status = 'scheduled' / 'dlq'
    end
```

## Retry and DLQ Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Queued
    Queued --> Claimed : Worker picks up
    Claimed --> Running : Execution starts
    Running --> Completed : Success
    Running --> Failed : Exception thrown
    
    Failed --> Scheduled : Max retries not reached (Exponential Backoff)
    Scheduled --> Queued : Delay elapsed (Promoter)
    
    Failed --> DLQ : Max retries exceeded
    DLQ --> [*]
    Completed --> [*]
```
