"""
RetryPromoter — Background task that promotes delayed-retry jobs back to queued.

On each tick (every 15 seconds):
1. Queries Jobs where status='scheduled' AND scheduled_at <= now()
2. Updates those jobs to status='queued' so workers can pick them up
3. Uses SELECT FOR UPDATE SKIP LOCKED for multi-instance safety

This solves the critical gap where failed jobs that get rescheduled for retry
(status=scheduled, scheduled_at=future) would otherwise be stuck forever because
the worker's claim_next_job only selects status='queued' jobs.
"""
import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select, update

from app.database.session import AsyncSessionLocal
from app.models.job import Job, JobLog

logger = logging.getLogger("retry_promoter")


class RetryPromoter:
    def __init__(self, tick_interval: int = 15):
        """
        Args:
            tick_interval: How often (in seconds) to check for due retry jobs.
                           Defaults to 15s for reasonably fast retry pickup.
        """
        self.tick_interval = tick_interval
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        logger.info("RetryPromoter starting (tick interval: %ds)", self.tick_interval)
        self._running = True
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        logger.info("RetryPromoter stopping...")
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("RetryPromoter stopped.")

    async def _loop(self) -> None:
        while self._running:
            try:
                await self._tick()
            except Exception:
                logger.exception("Unexpected error in RetryPromoter tick")
            await asyncio.sleep(self.tick_interval)

    async def _tick(self) -> None:
        """Promote all due scheduled-retry jobs back to queued status."""
        now = datetime.now(timezone.utc)

        async with AsyncSessionLocal() as session:
            # Find all jobs that are in scheduled state with a past scheduled_at
            # Use FOR UPDATE SKIP LOCKED to prevent race conditions across multiple
            # API instances running their own RetryPromoter loops.
            stmt = (
                select(Job)
                .where(Job.status == "scheduled")
                .where(Job.scheduled_at <= now)
                .with_for_update(skip_locked=True)
            )
            result = await session.execute(stmt)
            due_jobs = result.scalars().all()

            if not due_jobs:
                return

            promoted_count = 0
            for job in due_jobs:
                job.status = "queued"
                log = JobLog(
                    job_id=job.id,
                    message=f"Retry delay elapsed — job re-queued after {job.current_retries} attempt(s).",
                )
                session.add(log)
                promoted_count += 1

            await session.commit()
            if promoted_count > 0:
                logger.info("RetryPromoter promoted %d job(s) from scheduled → queued", promoted_count)
