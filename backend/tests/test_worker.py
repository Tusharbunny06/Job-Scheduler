import pytest
import asyncio
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.repositories.job_repository import JobRepository
from app.schemas.job import JobCreate
from app.models.queue import Queue
from app.models.project import Project
from app.models.organization import Organization
from app.models.queue import RetryPolicy
from app.models.job import Job
from app.models.worker import Worker
from app.scheduler.retry_promoter import RetryPromoter

@pytest.mark.asyncio
async def test_atomic_claim(db_session: AsyncSession):
    # Setup Data
    org = Organization(name="Test Org")
    db_session.add(org)
    await db_session.flush()

    proj = Project(name="Test Proj", organization_id=org.id)
    db_session.add(proj)
    await db_session.flush()

    queue = Queue(name="Test Queue", project_id=proj.id)
    db_session.add(queue)
    await db_session.flush()
    queue_id = queue.id

    # Need retry policy due to repository fetching it
    retry = RetryPolicy(queue_id=queue.id, max_retries=3)
    db_session.add(retry)
    
    # Create workers for claiming
    worker1 = Worker(hostname="w1", status="active", concurrency_limit=10)
    worker2 = Worker(hostname="w2", status="active", concurrency_limit=10)
    db_session.add(worker1)
    db_session.add(worker2)
    await db_session.flush()
    worker1_id = worker1.id
    worker2_id = worker2.id
    
    await db_session.commit()

    job_repo = JobRepository(db_session)
    job_in = JobCreate(queue_id=queue_id, payload={"test": "data"})
    db_job = await job_repo.create(job_in)
    
    assert db_job.status == "queued"
    db_job_id = db_job.id

    # Claim job
    job1, _ = await job_repo.claim_next_job(worker1_id)
    job2, _ = await job_repo.claim_next_job(worker2_id)

    # Worker 1 should get the job
    assert job1 is not None
    assert job1.id == db_job_id
    assert job1.status == "claimed"

    # Worker 2 should get nothing because it's skipped/locked/claimed
    assert job2 is None


@pytest.mark.asyncio
async def test_retry_promoter_promotes_due_jobs(db_session: AsyncSession):
    """
    RetryPromoter should move jobs from scheduled->queued when scheduled_at has passed.
    This tests the critical reliability fix: retry-delayed jobs must eventually be picked up.
    """
    org = Organization(name="Promoter Test Org")
    db_session.add(org)
    await db_session.flush()

    proj = Project(name="Promoter Test Project", organization_id=org.id)
    db_session.add(proj)
    await db_session.flush()

    queue = Queue(name="promoter-queue", project_id=proj.id)
    db_session.add(queue)
    await db_session.flush()
    queue_id = queue.id
    await db_session.commit()

    # Create a job that simulates a retry-scheduled state (scheduled_at in the past)
    past_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    job = Job(
        queue_id=queue_id,
        payload={"retry": True},
        status="scheduled",
        scheduled_at=past_time,
        max_retries=3,
        current_retries=1,
    )
    db_session.add(job)
    await db_session.flush()
    job_id = job.id
    await db_session.commit()

    # Trigger the retry promoter tick
    promoter = RetryPromoter(tick_interval=9999)
    await promoter._tick()
    
    # Clear SQLAlchemy cache since promoter uses a different session
    db_session.expire_all()

    # Job should now be queued
    stmt = select(Job).where(Job.id == job_id)
    result = await db_session.execute(stmt)
    updated_job = result.scalars().first()

    assert updated_job.status == "queued", (
        "RetryPromoter should have promoted the scheduled job to queued status"
    )


@pytest.mark.asyncio
async def test_retry_promoter_skips_future_jobs(db_session: AsyncSession):
    """RetryPromoter should NOT promote jobs scheduled for the future."""
    org = Organization(name="Future Test Org")
    db_session.add(org)
    await db_session.flush()

    proj = Project(name="Future Test Project", organization_id=org.id)
    db_session.add(proj)
    await db_session.flush()

    queue = Queue(name="future-queue", project_id=proj.id)
    db_session.add(queue)
    await db_session.flush()
    queue_id = queue.id
    await db_session.commit()

    future_time = datetime.now(timezone.utc) + timedelta(minutes=30)
    job = Job(
        queue_id=queue_id,
        payload={"future": True},
        status="scheduled",
        scheduled_at=future_time,
        max_retries=3,
        current_retries=1,
    )
    db_session.add(job)
    await db_session.flush()
    job_id = job.id
    await db_session.commit()

    promoter = RetryPromoter(tick_interval=9999)
    await promoter._tick()
    
    # Clear SQLAlchemy cache since promoter uses a different session
    db_session.expire_all()

    stmt = select(Job).where(Job.id == job_id)
    result = await db_session.execute(stmt)
    updated_job = result.scalars().first()

    assert updated_job.status == "scheduled", (
        "Future-scheduled jobs should remain in scheduled state"
    )


@pytest.mark.asyncio
async def test_job_priority_ordering(db_session: AsyncSession):
    """Higher priority jobs should be claimed before lower priority ones."""
    org = Organization(name="Priority Test Org")
    db_session.add(org)
    await db_session.flush()

    proj = Project(name="Priority Test Project", organization_id=org.id)
    db_session.add(proj)
    await db_session.flush()

    queue = Queue(name="priority-queue", project_id=proj.id)
    db_session.add(queue)
    await db_session.flush()
    queue_id = queue.id
    
    worker = Worker(hostname="priority-worker", status="active", concurrency_limit=10)
    db_session.add(worker)
    await db_session.flush()
    worker_id = worker.id
    
    await db_session.commit()

    # Create low priority job first
    low_job = Job(queue_id=queue_id, payload={"priority": "low"}, status="queued", priority=0)
    db_session.add(low_job)
    await db_session.flush()
    low_job_id = low_job.id

    # Create high priority job second
    high_job = Job(queue_id=queue_id, payload={"priority": "high"}, status="queued", priority=10)
    db_session.add(high_job)
    await db_session.flush()
    high_job_id = high_job.id
    await db_session.commit()

    job_repo = JobRepository(db_session)
    claimed, _ = await job_repo.claim_next_job(worker_id)

    assert claimed is not None
    assert claimed.id == high_job_id, "High priority job should be claimed first"
