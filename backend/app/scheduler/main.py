import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import asyncio
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.database.session import AsyncSessionLocal
from app.models.job import Job

from app.scheduler.cron_scheduler import CronScheduler
from app.scheduler.retry_promoter import RetryPromoter
from app.scheduler.stale_job_reclaimer import StaleJobReclaimer

class SchedulerService:
    def __init__(self):
        self.is_running = False
        self.cron = CronScheduler()
        self.retry_promoter = RetryPromoter()
        self.stale_reclaimer = StaleJobReclaimer()

    async def process_scheduled_jobs(self):
        while self.is_running:
            try:
                async with AsyncSessionLocal() as session:
                    # Find jobs that are scheduled and ready to run
                    stmt = (
                        select(Job)
                        .where(Job.status == "scheduled")
                        .where(Job.scheduled_at <= datetime.now(timezone.utc))
                    )
                    result = await session.execute(stmt)
                    jobs_to_queue = result.scalars().all()

                    for job in jobs_to_queue:
                        print(f"Moving job {job.id} from scheduled to queued.")
                        job.status = "queued"
                        job.scheduled_at = None

                    await session.commit()
            except Exception as e:
                print(f"Scheduler error: {e}")
                
            # Sleep before next check
            await asyncio.sleep(5)

    async def start(self):
        print("Starting scheduler daemon...")
        self.is_running = True
        asyncio.create_task(self.process_scheduled_jobs())
        await self.cron.start()
        await self.retry_promoter.start()
        await self.stale_reclaimer.start()
        
    async def stop(self):
        print("Stopping scheduler daemon...")
        self.is_running = False
        await self.cron.stop()
        await self.retry_promoter.stop()
        await self.stale_reclaimer.stop()

async def main():
    scheduler = SchedulerService()
    await scheduler.start()
    
    stop_event = asyncio.Event()
    
    import signal
    def handle_shutdown(signum, frame):
        print("\nReceived stop signal. Shutting down scheduler...")
        stop_event.set()
        
    try:
        signal.signal(signal.SIGINT, handle_shutdown)
        signal.signal(signal.SIGTERM, handle_shutdown)
    except NotImplementedError:
        pass
        
    await stop_event.wait()
    await scheduler.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Interrupted")
