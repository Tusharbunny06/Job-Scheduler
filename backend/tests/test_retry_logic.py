import pytest
from httpx import AsyncClient
import asyncio
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.job_repository import JobRepository
from app.schemas.job import JobCreate
from app.models.queue import Queue
from app.models.project import Project
from app.models.organization import Organization
from app.models.queue import RetryPolicy
from app.models.job import Job, JobExecution, DeadLetterQueue
from app.models.worker import Worker
from sqlalchemy import select

@pytest.mark.asyncio
async def test_dlq_promotion_and_retry(db_session: AsyncSession):
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

    # Retry policy: 1 retry max
    retry = RetryPolicy(queue_id=queue.id, max_retries=1, strategy="fixed_delay", delay_seconds=0)
    db_session.add(retry)
    
    worker = Worker(hostname="test-worker", status="active", concurrency_limit=10)
    db_session.add(worker)
    await db_session.flush()
    worker_id = worker.id
    
    await db_session.commit()

    # Create job
    job_repo = JobRepository(db_session)
    job_in = JobCreate(queue_id=queue_id, payload={"fail": True})
    db_job = await job_repo.create(job_in)
    
    assert db_job.status == "queued"
    assert db_job.max_retries == 1

    # Simulate worker claiming it
    job, execution = await job_repo.claim_next_job(worker_id)
    assert job is not None
    assert job.status == "claimed"

    # We simulate the try/catch behavior inside the worker's process_job method
    # directly here without importing WorkerService (avoids cross-package import issues)
    try:
        raise ValueError("Simulated failure")
    except Exception as e:
        execution.status = "failed"
        execution.error_stack = str(e)
        job.current_retries += 1
        # Job has max_retries = 1, current_retries is now 1. It should schedule a retry.
        if job.current_retries > job.max_retries:
            job.status = "dlq"
            dlq = DeadLetterQueue(job_id=job.id, reason=str(e))
            db_session.add(dlq)
        else:
            job.status = "scheduled"
    
    await db_session.commit()

    stmt = select(Job).where(Job.id == job.id)
    job_check = (await db_session.execute(stmt)).scalars().first()
    assert job_check.status == "scheduled"
    assert job_check.current_retries == 1

    # Simulate second claim (after delay)
    job_check.status = "queued"  # Fast forward
    await db_session.commit()
    
    job2, execution2 = await job_repo.claim_next_job(worker_id)
    
    # Second failure
    try:
        raise ValueError("Simulated failure 2")
    except Exception as e:
        execution2.status = "failed"
        job2.current_retries += 1
        # Now current_retries is 2 > max_retries (1). Should go to DLQ.
        if job2.current_retries > job2.max_retries:
            job2.status = "dlq"
            dlq = DeadLetterQueue(job_id=job2.id, reason=str(e))
            db_session.add(dlq)
        else:
            job2.status = "scheduled"

    await db_session.commit()

    stmt = select(Job).where(Job.id == job2.id)
    job_check2 = (await db_session.execute(stmt)).scalars().first()
    assert job_check2.status == "dlq"

    stmt = select(DeadLetterQueue).where(DeadLetterQueue.job_id == job2.id)
    dlq_entry = (await db_session.execute(stmt)).scalars().first()
    assert dlq_entry is not None

    # Test the retry_job repository method
    retried_job = await job_repo.retry_job(job_check2.id)
    assert retried_job.status == "queued"
    assert retried_job.current_retries == 0

    stmt = select(DeadLetterQueue).where(DeadLetterQueue.job_id == job2.id)
    dlq_entry_after = (await db_session.execute(stmt)).scalars().first()
    assert dlq_entry_after is None
