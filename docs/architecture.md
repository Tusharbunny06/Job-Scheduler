# Architecture

The Job Scheduler uses a robust, scalable architecture separated into distinct logical components.

## High Level Architecture

```mermaid
graph TD
    classDef frontend fill:#1e293b,stroke:#4ade80,stroke-width:2px,color:#fff;
    classDef backend fill:#1e293b,stroke:#60a5fa,stroke-width:2px,color:#fff;
    classDef daemon fill:#1e293b,stroke:#f472b6,stroke-width:2px,color:#fff;
    classDef db fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#fff;

    subgraph Frontend["Frontend (Vite + React)"]
        UI_Auth["Login & Auth"]
        UI_Layout["Main Dashboard"]
        UI_Jobs["Job Explorer"]
        UI_Queues["Queue Manager"]
        UI_Cron["Recurring Rules"]
        
        UI_Auth --> UI_Layout
        UI_Layout --> UI_Jobs & UI_Queues & UI_Cron
    end

    subgraph Backend["Backend (FastAPI REST API)"]
        API_Router["REST Router Endpoints"]
        API_Auth["JWT Verification Middleware"]
        API_Controllers["CRUD API Controllers"]
        API_ORM["SQLAlchemy ORM"]

        API_Router --> API_Auth --> API_Controllers --> API_ORM
    end

    UI_Jobs -.->|HTTP Requests| API_Router

    subgraph Workers["Background Worker Daemon"]
        W_Poll["Polling Engine (1s)"]
        W_Exec["Job Execution Sandbox"]
        W_Retry["Stats & Retry Manager"]
        W_Ping["Heartbeat Ping Loop (5s)"]

        W_Poll -->|Pass Payload| W_Exec -->|On Failure/Success| W_Retry
    end

    subgraph Scheduler["Background System Daemons"]
        S_Cron["Cron Scheduler Coordinator"]
        S_Sweep["Worker Heartbeat Sweeper"]
    end

    subgraph Database["PostgreSQL Database"]
        DB_User[("Users & Orgs")]
        DB_Queue[("Queues & Policies")]
        DB_Job[("Job Table (Indexed)")]
        DB_DLQ[("Dead Letter Queue")]
        DB_Worker[("Worker Registry")]
        DB_Log[("Execution Logs")]
    end

    %% Backend to DB
    API_ORM --> DB_User & DB_Queue & DB_Job

    %% Worker to DB
    W_Poll -->|SELECT FOR UPDATE SKIP LOCKED| DB_Job
    W_Exec -->|INSERT Execution Message| DB_Log
    W_Retry -->|Calculate Backoffs & Offload| DB_DLQ & DB_Job
    W_Ping -->|UPDATE active registration| DB_Worker

    %% Scheduler to DB
    S_Cron -->|INSERT compound job copy| DB_Job
    S_Sweep -->|UPDATE offline worker nodes| DB_Worker
    S_Sweep -->|UPDATE stuck jobs| DB_Job

    %% Apply Classes
    class UI_Auth,UI_Layout,UI_Jobs,UI_Queues,UI_Cron frontend;
    class API_Router,API_Auth,API_Controllers,API_ORM backend;
    class W_Poll,W_Exec,W_Retry,W_Ping,S_Cron,S_Sweep daemon;
    class DB_User,DB_Queue,DB_Job,DB_DLQ,DB_Worker,DB_Log db;
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
