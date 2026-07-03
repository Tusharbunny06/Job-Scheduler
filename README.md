# Job Scheduler

A robust, distributed background job scheduler built with FastAPI, PostgreSQL, and React. It provides functionality similar to Sidekiq, Celery, BullMQ, or AWS SQS.

## Features

- **Authentication & RBAC**: JWT-based login, isolated projects by user organization.
- **Queue Management**: Priority levels, concurrency limits, and pausing/resuming queues.
- **Job Types**: Immediate, Delayed (Scheduled), Recurring (Cron), and Batch execution.
- **Reliable Worker Service**: Atomic job claiming (`SELECT FOR UPDATE SKIP LOCKED`) ensures a job is never processed twice.
- **Retry Strategies**: Fixed Delay, Linear Backoff, and Exponential Backoff.
- **Dead Letter Queue (DLQ)**: Permanently failed jobs are stored securely for later analysis and manual retry.
- **Resilience**: Workers send heartbeats. If a worker crashes, a Stale Job Reclaimer resets its jobs so they can be processed again.
- **Comprehensive UI**: Live throughput graphs, execution history, logs, and queue configuration.

## System Architecture

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

## Getting Started

### 1. Prerequisites
- Docker & Docker Compose (for PostgreSQL).
- Python 3.11+
- Node.js 18+

### 2. Start PostgreSQL
```bash
docker-compose up -d
```

### 3. Configure Environment Variables
```bash
cd backend
cp .env.example .env
# Edit .env and set your own POSTGRES_PASSWORD and SECRET_KEY
```

> **Important**: Never commit your `.env` file. It is listed in `.gitignore`.

### 4. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start API Server (Terminal 1)
uvicorn app.main:app --reload

# Start Scheduler Daemon (Terminal 2)
# Handles cron jobs, retries, and reclaiming jobs from dead workers
python app/scheduler/main.py
```

### 5. Worker Setup
The worker is a separate process that pulls jobs from the database and executes them.
```bash
cd worker
python main.py
```

### 5. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

## Documentation

For a detailed view of the architecture and database schema, see the `/docs` directory.
- [Architecture & Sequence Diagrams](docs/architecture.md)
- [Database ER Diagram](docs/database.md)

## Tradeoffs & Design Decisions
- **Database as a Message Broker**: We use PostgreSQL as the queue instead of Redis or RabbitMQ to simplify infrastructure and take advantage of ACID properties. The use of `SKIP LOCKED` ensures high concurrency without deadlocks, though it may not scale to tens of thousands of jobs per second like a dedicated message broker could.
- **Polling vs Push**: Workers poll the database for new jobs instead of receiving pushes. This is simpler to implement and naturally handles backpressure, but introduces a small delay (up to the polling interval).
- **Separation of Concerns**: The scheduler is separated from the API and worker. This allows scaling workers independently of the scheduler (which must be a singleton or use leader election in production).
