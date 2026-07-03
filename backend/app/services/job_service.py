"""
Job Service — encapsulates business logic for job operations.
Routers call this layer; repositories handle DB interactions.
"""
from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.job_repository import JobRepository
from app.schemas.job import JobCreate, JobBatchCreate
from app.models.job import Job


class JobService:
    def __init__(self, db: AsyncSession):
        self.repo = JobRepository(db)

    async def create_job(self, job_in: JobCreate) -> Job:
        """Create a single job, setting status based on scheduled_at."""
        return await self.repo.create(job_in)

    async def create_batch(self, batch: JobBatchCreate) -> List[Job]:
        """Atomically create multiple jobs. All succeed or none are committed."""
        if not batch.jobs:
            raise HTTPException(status_code=400, detail="Batch must contain at least one job.")
        return await self.repo.create_batch(batch.jobs)

    async def retry_job(self, job_id: UUID) -> Job:
        """
        Reset a failed or DLQ job to queued.
        Clears the DLQ entry and resets retry counter.
        Raises 404 if not found, 400 if job is not in a retryable state.
        """
        job = await self.repo.get_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found.")
        if job.status not in ("failed", "dlq"):
            raise HTTPException(
                status_code=400,
                detail=f"Job is in status '{job.status}' and cannot be retried. Only failed or dlq jobs can be retried."
            )
        retried = await self.repo.retry_job(job_id)
        return retried
