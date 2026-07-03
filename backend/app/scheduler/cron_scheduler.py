"""
CronScheduler — Background task that dispatches recurring jobs.

On each tick (every 30 seconds):
1. Queries ScheduledJobs where next_run_at <= now() AND is_active=True
2. Creates a new Job instance (status=queued) for each due entry
3. Updates next_run_at to the next cron fire time using croniter
4. Updates last_run_at to track audit trail
5. Commits atomically so partial failures don't cause double-dispatch

This runs inside the FastAPI process via asyncio and is started/stopped
via the app lifespan context manager in main.py.

Multi-instance safety: SELECT ... FOR UPDATE SKIP LOCKED ensures that when
multiple API instances are running, only one will dispatch each scheduled job.
"""
import asyncio
import logging
from datetime import datetime, timezone

from croniter import croniter
from sqlalchemy import select

from app.database.session import AsyncSessionLocal
from app.models.job import Job, JobLog, ScheduledJob

logger = logging.getLogger("cron_scheduler")


class CronScheduler:
    def __init__(self, tick_interval: int = 30):
        """
        Args:
            tick_interval: How often (in seconds) to check for due scheduled jobs.
                           Defaults to 30s — sub-minute precision isn't meaningful for cron.
        """
        self.tick_interval = tick_interval
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        logger.info("CronScheduler starting (tick interval: %ds)", self.tick_interval)
        self._running = True
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        logger.info("CronScheduler stopping...")
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("CronScheduler stopped.")

    async def _loop(self) -> None:
        while self._running:
            try:
                await self._tick()
            except Exception:
                logger.exception("Unexpected error in CronScheduler tick")
            await asyncio.sleep(self.tick_interval)

    async def _tick(self) -> None:
        """Check for due active ScheduledJobs and enqueue new Job instances."""
        now = datetime.now(timezone.utc)

        async with AsyncSessionLocal() as session:
            # Find all ACTIVE scheduled jobs whose next_run_at has passed.
            # is_active=False allows users to disable recurring jobs without deleting them.
            # SKIP LOCKED prevents race conditions with multiple app instances.
            stmt = (
                select(ScheduledJob)
                .where(ScheduledJob.next_run_at <= now)
                .where(ScheduledJob.is_active == True)  # noqa: E712
                .with_for_update(skip_locked=True)
            )
            result = await session.execute(stmt)
            due_jobs = result.scalars().all()

            if not due_jobs:
                return

            for sched in due_jobs:
                # Create a new queued Job
                new_job = Job(
                    queue_id=sched.queue_id,
                    payload=sched.payload,
                    status="queued",
                )
                session.add(new_job)

                # Advance next_run_at to the next cron fire time
                try:
                    cron = croniter(sched.cron_expression, now)
                    sched.next_run_at = cron.get_next(datetime)
                    sched.last_run_at = now  # Update audit timestamp
                except Exception:
                    logger.error(
                        "Invalid cron expression '%s' for ScheduledJob %s — skipping.",
                        sched.cron_expression,
                        sched.id,
                    )
                    continue

                # Flush to get new_job.id before creating the log
                await session.flush()

                log = JobLog(
                    job_id=new_job.id,
                    message=f"Job dispatched by CronScheduler from ScheduledJob {sched.id} (expr: {sched.cron_expression})",
                )
                session.add(log)
                logger.info(
                    "Dispatched job %s from cron %s (expr: %s, next: %s)",
                    new_job.id, sched.id, sched.cron_expression, sched.next_run_at
                )

            await session.commit()
