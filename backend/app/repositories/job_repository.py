from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from app.models.job import Job, JobExecution, JobLog, DeadLetterQueue
from app.schemas.job import JobCreate
from app.models.queue import Queue, RetryPolicy
from typing import List, Optional, Tuple
from uuid import UUID

class JobRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, job_id: UUID) -> Optional[Job]:
        stmt = select(Job).where(Job.id == job_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_all_by_queue(self, queue_id: UUID, skip: int = 0, limit: int = 100, status: Optional[str] = None) -> List[Job]:
        stmt = select(Job).where(Job.queue_id == queue_id)
        if status:
            stmt = stmt.where(Job.status == status)
        stmt = stmt.order_by(Job.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all(self, skip: int = 0, limit: int = 100, status: Optional[str] = None) -> List[Job]:
        stmt = select(Job)
        if status:
            stmt = stmt.where(Job.status == status)
        stmt = stmt.order_by(Job.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, job_in: JobCreate) -> Job:
        stmt = select(Queue).where(Queue.id == job_in.queue_id)
        queue = (await self.session.execute(stmt)).scalars().first()
        timeout = job_in.execution_timeout if job_in.execution_timeout else (queue.default_execution_timeout if queue else 3600)

        stmt = select(RetryPolicy).where(RetryPolicy.queue_id == job_in.queue_id)
        result = await self.session.execute(stmt)
        retry_policy = result.scalars().first()
        max_retries = retry_policy.max_retries if retry_policy else 0
        
        db_job = Job(
            queue_id=job_in.queue_id,
            payload=job_in.payload,
            status="scheduled" if job_in.scheduled_at else "queued",
            scheduled_at=job_in.scheduled_at,
            max_retries=max_retries,
            priority=job_in.priority,
            execution_timeout=timeout,
        )
        self.session.add(db_job)
        await self.session.commit()
        await self.session.refresh(db_job)
        return db_job

    async def create_batch(self, jobs_in: List[JobCreate]) -> List[Job]:
        """Atomically create multiple jobs in one transaction."""
        created = []
        for job_in in jobs_in:
            stmt = select(Queue).where(Queue.id == job_in.queue_id)
            queue = (await self.session.execute(stmt)).scalars().first()
            timeout = job_in.execution_timeout if job_in.execution_timeout else (queue.default_execution_timeout if queue else 3600)

            stmt = select(RetryPolicy).where(RetryPolicy.queue_id == job_in.queue_id)
            result = await self.session.execute(stmt)
            retry_policy = result.scalars().first()
            max_retries = retry_policy.max_retries if retry_policy else 0

            db_job = Job(
                queue_id=job_in.queue_id,
                payload=job_in.payload,
                status="scheduled" if job_in.scheduled_at else "queued",
                scheduled_at=job_in.scheduled_at,
                max_retries=max_retries,
                priority=job_in.priority,
                execution_timeout=timeout,
            )
            self.session.add(db_job)
            created.append(db_job)

        await self.session.commit()
        for job in created:
            await self.session.refresh(job)
        return created

    async def get_logs(self, job_id: UUID) -> List[JobLog]:
        stmt = select(JobLog).where(JobLog.job_id == job_id).order_by(JobLog.timestamp.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_executions(self, job_id: UUID) -> List[JobExecution]:
        stmt = select(JobExecution).where(JobExecution.job_id == job_id).order_by(JobExecution.started_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def retry_job(self, job_id: UUID) -> Optional[Job]:
        """Reset a failed/DLQ job back to queued, clearing its DLQ entry."""
        job = await self.get_by_id(job_id)
        if not job:
            return None
        if job.status not in ("failed", "dlq"):
            return None

        # Remove DLQ entry if present
        await self.session.execute(delete(DeadLetterQueue).where(DeadLetterQueue.job_id == job_id))

        job.status = "queued"
        job.current_retries = 0
        job.scheduled_at = None

        log = JobLog(job_id=job.id, message="Job manually retried by user.")
        self.session.add(log)
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def claim_next_job(self, worker_id: UUID) -> Tuple[Optional[Job], Optional[JobExecution]]:
        """
        Atomically claim the next available job from a non-paused queue.
        Uses SELECT FOR UPDATE SKIP LOCKED to prevent duplicate execution.
        
        Priority ordering: Job.priority DESC > Queue.priority DESC > Job.created_at ASC
        This allows both queue-level and job-level priority to be respected.
        """
        stmt = (
            select(Job)
            .join(Queue, Job.queue_id == Queue.id)
            .where(Job.status == "queued")
            .where(Queue.is_paused == False)  # noqa: E712 — SQLAlchemy requires == False
            .order_by(Job.priority.desc(), Queue.priority.desc(), Job.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        
        result = await self.session.execute(stmt)
        job = result.scalars().first()
        
        if job:
            job.status = "claimed"
            db_execution = JobExecution(
                job_id=job.id,
                worker_id=worker_id,
                status="running"
            )
            self.session.add(db_execution)
            await self.session.commit()
            await self.session.refresh(job)
            await self.session.refresh(db_execution)
            return job, db_execution
        return None, None
