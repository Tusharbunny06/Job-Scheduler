"""
Metrics API — Dashboard metrics, throughput, worker status, and system health.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Annotated, Dict, Any, List
from datetime import datetime, timezone, timedelta

from app.database.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.worker import Worker
from app.models.job import Job, JobExecution

router = APIRouter()


@router.get(
    "/dashboard",
    summary="Get dashboard overview metrics",
    description="Returns active worker count, queued jobs, failure rate, and jobs completed in the last hour.",
)
async def get_dashboard_metrics(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    two_mins_ago = now - timedelta(minutes=2)
    one_hour_ago = now - timedelta(hours=1)

    # Active workers: heartbeat within last 2 minutes
    stmt_workers = (
        select(func.count(Worker.id))
        .where(Worker.status == "active", Worker.last_heartbeat >= two_mins_ago)
    )
    active_workers = (await db.execute(stmt_workers)).scalar() or 0

    # Queued jobs
    stmt_queued = select(func.count(Job.id)).where(Job.status == "queued")
    jobs_queued = (await db.execute(stmt_queued)).scalar() or 0

    # Running jobs
    stmt_running = select(func.count(Job.id)).where(Job.status == "running")
    jobs_running = (await db.execute(stmt_running)).scalar() or 0

    # Completed in last hour (throughput)
    stmt_completed = (
        select(func.count(JobExecution.id))
        .where(JobExecution.status == "completed", JobExecution.completed_at >= one_hour_ago)
    )
    completed_last_hour = (await db.execute(stmt_completed)).scalar() or 0

    # Failure rate
    stmt_failed = select(func.count(JobExecution.id)).where(JobExecution.status == "failed")
    failed_executions = (await db.execute(stmt_failed)).scalar() or 0

    stmt_all_execs = select(func.count(JobExecution.id))
    all_executions = (await db.execute(stmt_all_execs)).scalar() or 0

    failure_rate = 0.0
    if all_executions > 0:
        failure_rate = round((failed_executions / all_executions) * 100, 2)

    # Average execution duration in seconds
    stmt_avg_duration = select(
        func.avg(
            func.extract("epoch", JobExecution.completed_at) -
            func.extract("epoch", JobExecution.started_at)
        )
    ).where(JobExecution.status == "completed", JobExecution.completed_at.isnot(None))
    avg_duration_raw = (await db.execute(stmt_avg_duration)).scalar()
    avg_duration_seconds = round(float(avg_duration_raw), 2) if avg_duration_raw else 0.0

    # DLQ count
    stmt_dlq = select(func.count(Job.id)).where(Job.status == "dlq")
    dlq_count = (await db.execute(stmt_dlq)).scalar() or 0

    return {
        "active_workers": active_workers,
        "jobs_queued": jobs_queued,
        "jobs_running": jobs_running,
        "completed_last_hour": completed_last_hour,
        "failure_rate": f"{failure_rate}%",
        "failure_rate_value": failure_rate,
        "avg_execution_seconds": avg_duration_seconds,
        "dlq_count": dlq_count,
        "total_executions": all_executions,
    }


@router.get(
    "/workers",
    summary="List all registered workers",
    description="Returns all workers with their status and last heartbeat timestamp. Workers with heartbeat older than 2 minutes are considered stale.",
)
async def list_workers(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> List[Dict[str, Any]]:
    stmt = select(Worker).order_by(Worker.last_heartbeat.desc())
    result = await db.execute(stmt)
    workers = result.scalars().all()

    two_mins_ago = datetime.now(timezone.utc) - timedelta(minutes=2)

    return [
        {
            "id": str(w.id),
            "hostname": w.hostname,
            "status": w.status,
            "concurrency_limit": w.concurrency_limit,
            "registered_at": w.registered_at.isoformat() if w.registered_at else None,
            "last_heartbeat": w.last_heartbeat.isoformat() if w.last_heartbeat else None,
            "is_stale": (
                w.last_heartbeat is None or
                w.last_heartbeat.replace(tzinfo=timezone.utc) < two_mins_ago
            ),
        }
        for w in workers
    ]


@router.get(
    "/throughput",
    summary="Get hourly job throughput for the past 24 hours",
    description="Returns completed job counts bucketed by hour, useful for time-series charts.",
)
async def get_throughput(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> List[Dict[str, Any]]:
    now = datetime.now(timezone.utc)
    buckets = []

    for i in range(23, -1, -1):
        bucket_start = now - timedelta(hours=i + 1)
        bucket_end = now - timedelta(hours=i)
        label = bucket_end.strftime("%H:00")

        stmt = (
            select(func.count(JobExecution.id))
            .where(
                JobExecution.status == "completed",
                JobExecution.completed_at >= bucket_start,
                JobExecution.completed_at < bucket_end,
            )
        )
        count = (await db.execute(stmt)).scalar() or 0
        buckets.append({"hour": label, "completed": count})

    return buckets
