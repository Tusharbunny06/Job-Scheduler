"""
StaleJobReclaimer — Background task that reclaims jobs from dead workers.

Workers periodically update their last_heartbeat. If a worker crashes,
it stops sending heartbeats. The jobs it claimed remain in the 'running'
state forever.

This daemon runs periodically to:
1. Find workers whose last_heartbeat is older than a threshold (e.g., 5 mins).
2. Mark those workers as 'offline' or 'dead'.
3. Find any JobExecutions associated with those workers that are still 'running'.
4. Mark those JobExecutions as 'failed' (Worker crashed).
5. Move the corresponding Jobs back to 'queued' (or apply retry logic).
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import AsyncSessionLocal
from app.models.worker import Worker
from app.models.job import Job, JobExecution, JobLog

logger = logging.getLogger("stale_job_reclaimer")

class StaleJobReclaimer:
    def __init__(self, check_interval: int = 60, timeout_minutes: int = 5):
        """
        Args:
            check_interval: How often (in seconds) to check for stale workers.
            timeout_minutes: How many minutes without a heartbeat before a worker is considered dead.
        """
        self.check_interval = check_interval
        self.timeout_minutes = timeout_minutes
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        logger.info("StaleJobReclaimer starting (timeout: %d min)", self.timeout_minutes)
        self._running = True
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        logger.info("StaleJobReclaimer stopping...")
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("StaleJobReclaimer stopped.")

    async def _loop(self) -> None:
        while self._running:
            try:
                await self._tick()
            except Exception:
                logger.exception("Unexpected error in StaleJobReclaimer tick")
            await asyncio.sleep(self.check_interval)

    async def _tick(self) -> None:
        """Find dead workers, fail their executions, and requeue their jobs."""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=self.timeout_minutes)

        async with AsyncSessionLocal() as session:
            # 1. Find stale workers
            stmt = select(Worker).where(
                Worker.last_heartbeat < cutoff,
                Worker.status == "active"
            )
            result = await session.execute(stmt)
            stale_workers = result.scalars().all()

            if not stale_workers:
                return

            reclaimed_jobs_count = 0

            for worker in stale_workers:
                worker.status = "offline"
                
                # 2. Find running executions for this worker
                stmt_exec = select(JobExecution).where(
                    JobExecution.worker_id == worker.id,
                    JobExecution.status == "running"
                )
                exec_result = await session.execute(stmt_exec)
                running_executions = exec_result.scalars().all()

                for execution in running_executions:
                    execution.status = "failed"
                    execution.error_stack = "Worker node crashed or stopped sending heartbeats."
                    execution.completed_at = now

                    # 3. Find the corresponding job and set it back to queued
                    stmt_job = select(Job).where(Job.id == execution.job_id)
                    job_result = await session.execute(stmt_job)
                    job = job_result.scalars().first()

                    if job and job.status in ("claimed", "running"):
                        # Requeue the job. The normal retry mechanism could also be used here, 
                        # but typically a worker crash means the job should just be restarted
                        job.status = "queued"
                        job.current_retries += 1
                        
                        log = JobLog(
                            job_id=job.id,
                            message=f"Job reclaimed from dead worker (ID: {worker.id}). Re-queued."
                        )
                        session.add(log)
                        reclaimed_jobs_count += 1
            
            await session.commit()

            if reclaimed_jobs_count > 0:
                logger.info(
                    "StaleJobReclaimer marked %d worker(s) offline and reclaimed %d job(s)", 
                    len(stale_workers), reclaimed_jobs_count
                )
