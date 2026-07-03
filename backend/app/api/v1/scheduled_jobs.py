"""
Scheduled Jobs API — Create, list, update, and delete recurring cron jobs.

A ScheduledJob is a template that the CronScheduler uses to dispatch new Job
instances on a recurring schedule defined by a cron expression.

Example: POST /scheduled-jobs/ with cron_expression="0 * * * *" will create
a new queued Job every hour.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Annotated, List
from uuid import UUID
from datetime import datetime, timezone

from croniter import croniter

from app.database.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.job import ScheduledJob
from app.schemas.scheduled_job import (
    ScheduledJobCreate,
    ScheduledJobResponse,
    ScheduledJobUpdate,
)

router = APIRouter()


@router.post(
    "/",
    response_model=ScheduledJobResponse,
    status_code=201,
    summary="Create a recurring cron job",
    description=(
        "Create a new recurring job definition. The CronScheduler will dispatch "
        "a new queued Job on every cron tick. Use standard 5-field cron expressions "
        "(e.g. '0 * * * *' for every hour, '*/5 * * * *' for every 5 minutes)."
    ),
)
async def create_scheduled_job(
    job_in: ScheduledJobCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    now = datetime.now(timezone.utc)
    cron = croniter(job_in.cron_expression, now)
    next_run = cron.get_next(datetime)

    scheduled_job = ScheduledJob(
        queue_id=job_in.queue_id,
        name=job_in.name,
        payload=job_in.payload,
        cron_expression=job_in.cron_expression,
        next_run_at=next_run,
        is_active=True,
    )
    db.add(scheduled_job)
    await db.commit()
    await db.refresh(scheduled_job)
    return scheduled_job


@router.get(
    "/",
    response_model=List[ScheduledJobResponse],
    summary="List all recurring cron jobs",
    description="Returns all recurring job definitions. Supports pagination.",
)
async def list_scheduled_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    active_only: bool = Query(False, description="If true, only return active scheduled jobs"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(ScheduledJob)
    if active_only:
        stmt = stmt.where(ScheduledJob.is_active == True)  # noqa: E712
    stmt = stmt.order_by(ScheduledJob.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get(
    "/{scheduled_job_id}",
    response_model=ScheduledJobResponse,
    summary="Get a recurring cron job",
)
async def get_scheduled_job(
    scheduled_job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(ScheduledJob).where(ScheduledJob.id == scheduled_job_id)
    result = await db.execute(stmt)
    job = result.scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Scheduled job not found")
    return job


@router.patch(
    "/{scheduled_job_id}",
    response_model=ScheduledJobResponse,
    summary="Update a recurring cron job",
    description=(
        "Update the name, payload, active state, or cron expression. "
        "If cron_expression is changed, next_run_at is recalculated from now."
    ),
)
async def update_scheduled_job(
    scheduled_job_id: UUID,
    job_update: ScheduledJobUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    stmt = select(ScheduledJob).where(ScheduledJob.id == scheduled_job_id)
    result = await db.execute(stmt)
    job = result.scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Scheduled job not found")

    if job_update.name is not None:
        job.name = job_update.name
    if job_update.payload is not None:
        job.payload = job_update.payload
    if job_update.is_active is not None:
        job.is_active = job_update.is_active
    if job_update.cron_expression is not None:
        job.cron_expression = job_update.cron_expression
        # Recalculate next_run_at from now when cron expression changes
        now = datetime.now(timezone.utc)
        cron = croniter(job_update.cron_expression, now)
        job.next_run_at = cron.get_next(datetime)

    await db.commit()
    await db.refresh(job)
    return job


@router.delete(
    "/{scheduled_job_id}",
    status_code=204,
    summary="Delete a recurring cron job",
    description="Permanently removes the recurring job definition. Already-dispatched jobs are not affected.",
)
async def delete_scheduled_job(
    scheduled_job_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    stmt = select(ScheduledJob).where(ScheduledJob.id == scheduled_job_id)
    result = await db.execute(stmt)
    job = result.scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Scheduled job not found")
    await db.delete(job)
    await db.commit()
