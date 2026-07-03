"""
Jobs API — CRUD, batch creation, retry, execution logs, and history.
All state-mutating operations go through the JobService business layer.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, List, Optional
from uuid import UUID

from app.database.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.job import (
    JobCreate,
    JobBatchCreate,
    JobResponse,
    JobLogResponse,
    JobExecutionResponse,
)
from app.repositories.job_repository import JobRepository
from app.services.job_service import JobService

router = APIRouter()


# ─────────────────────────────────────────────────────────────
# List & Read
# ─────────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=List[JobResponse],
    summary="List all jobs",
    description="Returns all jobs across all queues. Supports pagination and optional status filter.",
)
async def list_all_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status: Optional[str] = Query(None, description="Filter by job status: queued, running, completed, failed, dlq"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = JobRepository(db)
    return await repo.get_all(skip=skip, limit=limit, status=status)


@router.get(
    "/queue/{queue_id}",
    response_model=List[JobResponse],
    summary="List jobs by queue",
    description="Returns all jobs belonging to a specific queue. Supports pagination and status filter.",
)
async def list_jobs_by_queue(
    queue_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = JobRepository(db)
    return await repo.get_all_by_queue(queue_id=queue_id, skip=skip, limit=limit, status=status)


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get job details",
)
async def get_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = JobRepository(db)
    job = await repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get(
    "/{job_id}/logs",
    response_model=List[JobLogResponse],
    summary="Get execution logs for a job",
    description="Returns all log entries emitted during the job's lifetime, in chronological order.",
)
async def get_job_logs(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = JobRepository(db)
    job = await repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return await repo.get_logs(job_id)


@router.get(
    "/{job_id}/executions",
    response_model=List[JobExecutionResponse],
    summary="Get execution history for a job",
    description="Returns all execution attempts for a job, newest first. Shows worker assignment, duration, and errors.",
)
async def get_job_executions(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = JobRepository(db)
    job = await repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return await repo.get_executions(job_id)


# ─────────────────────────────────────────────────────────────
# Create
# ─────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=JobResponse,
    status_code=201,
    summary="Create a job",
    description="Create a single immediate, delayed, or scheduled job. Set `scheduled_at` for delayed execution.",
)
async def create_job(
    job_in: JobCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    service = JobService(db)
    return await service.create_job(job_in)


@router.post(
    "/batch",
    response_model=List[JobResponse],
    status_code=201,
    summary="Create a batch of jobs",
    description="Atomically create multiple jobs in a single request. All jobs are committed or none are. Maximum 500 jobs per batch.",
)
async def create_batch_jobs(
    batch: JobBatchCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    if len(batch.jobs) > 500:
        raise HTTPException(status_code=400, detail="Batch size cannot exceed 500 jobs.")
    service = JobService(db)
    return await service.create_batch(batch)


# ─────────────────────────────────────────────────────────────
# Actions
# ─────────────────────────────────────────────────────────────

@router.post(
    "/{job_id}/retry",
    response_model=JobResponse,
    summary="Retry a failed or DLQ job",
    description="Resets the job status back to queued and clears any Dead Letter Queue entry. Only works on failed or dlq jobs.",
)
async def retry_job(
    job_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    service = JobService(db)
    return await service.retry_job(job_id)
