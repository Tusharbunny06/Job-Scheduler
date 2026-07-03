import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

import asyncio
import traceback
import socket
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, select

from app.database.session import AsyncSessionLocal
from app.models.worker import Worker
from app.models.job import JobExecution, DeadLetterQueue, JobLog, Job
from app.models.queue import RetryPolicy
from app.repositories.job_repository import JobRepository

class WorkerService:
    def __init__(self, concurrency_limit: int = 10):
        self.worker_id = uuid4()
        self.hostname = socket.gethostname()
        self.concurrency_limit = concurrency_limit
        self.is_running = False
        self.semaphore = asyncio.Semaphore(concurrency_limit)
        self.tasks = set()

    async def register_worker(self, session: AsyncSession):
        worker = Worker(
            id=self.worker_id,
            hostname=self.hostname,
            status="active",
            concurrency_limit=self.concurrency_limit,
        )
        session.add(worker)
        await session.commit()

    async def heartbeat(self):
        while self.is_running:
            try:
                async with AsyncSessionLocal() as session:
                    stmt = update(Worker).where(Worker.id == self.worker_id).values(
                        last_heartbeat=datetime.now(timezone.utc)
                    )
                    await session.execute(stmt)
                    await session.commit()
            except Exception as e:
                print(f"Heartbeat error: {e}")
            await asyncio.sleep(30)

    async def _fetch_retry_policy(self, session: AsyncSession, queue_id) -> RetryPolicy:
        stmt = select(RetryPolicy).where(RetryPolicy.queue_id == queue_id)
        result = await session.execute(stmt)
        return result.scalars().first()

    async def process_job(self, job_id, execution_id):
        async with AsyncSessionLocal() as session:
            job = None
            execution = None
            try:
                stmt = select(Job).where(Job.id == job_id)
                job = (await session.execute(stmt)).scalars().first()
                stmt_exec = select(JobExecution).where(JobExecution.id == execution_id)
                execution = (await session.execute(stmt_exec)).scalars().first()

                if not job or not execution:
                    return

                # Mark as running now (status was claimed when picked up)
                job.status = "running"
                await session.flush()

                print(f"Executing job {job.id} with payload {job.payload}")
                await asyncio.sleep(1)  # Simulated work — replace with real handler
                
                execution.status = "completed"
                execution.completed_at = datetime.now(timezone.utc)
                job.status = "completed"
                
                log = JobLog(job_id=job.id, message="Job completed successfully.")
                session.add(log)
                
            except Exception as e:
                error_stack = traceback.format_exc()
                if execution:
                    execution.status = "failed"
                    execution.error_stack = error_stack
                    execution.completed_at = datetime.now(timezone.utc)
                
                if job:
                    job.current_retries += 1
                    if job.current_retries > job.max_retries:
                        job.status = "dlq"
                        dlq = DeadLetterQueue(job_id=job.id, reason=str(e))
                        session.add(dlq)
                        log = JobLog(
                            job_id=job.id,
                            message=f"Job permanently failed after {job.current_retries} attempt(s). Moved to DLQ: {str(e)}"
                        )
                    else:
                        policy = await self._fetch_retry_policy(session, job.queue_id)
                        delay = 60
                        if policy:
                            if policy.strategy == "linear_backoff":
                                delay = policy.delay_seconds * job.current_retries
                            elif policy.strategy == "exponential_backoff":
                                delay = int(policy.delay_seconds * (policy.backoff_multiplier ** (job.current_retries - 1)))
                            else:
                                delay = policy.delay_seconds

                        job.status = "scheduled" 
                        job.scheduled_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
                        log = JobLog(
                            job_id=job.id,
                            message=f"Job failed (attempt {job.current_retries}/{job.max_retries}). Retry scheduled in {delay}s: {str(e)}"
                        )
                    session.add(log)
                
            finally:
                await session.commit()

    async def _safe_process_job(self, job_id, execution_id):
        async with self.semaphore:
            await self.process_job(job_id, execution_id)

    async def poll_queues(self):
        while self.is_running:
            try:
                if self.semaphore.locked():
                    await asyncio.sleep(1)
                    continue

                async with AsyncSessionLocal() as session:
                    job_repo = JobRepository(session)
                    job, execution = await job_repo.claim_next_job(self.worker_id)
                    
                    if job and execution:
                        task = asyncio.create_task(self._safe_process_job(job.id, execution.id))
                        self.tasks.add(task)
                        task.add_done_callback(self.tasks.discard)
                    else:
                        await asyncio.sleep(2)
            except Exception as e:
                print(f"Polling error: {e}")
                await asyncio.sleep(5)

    async def start(self):
        print(f"Starting worker {self.worker_id} on {self.hostname} (concurrency={self.concurrency_limit})")
        self.is_running = True
        
        async with AsyncSessionLocal() as session:
            await self.register_worker(session)
            
        asyncio.create_task(self.heartbeat())
        asyncio.create_task(self.poll_queues())
        
    async def stop(self):
        print("Stopping worker service...")
        self.is_running = False
        if self.tasks:
            print(f"Waiting for {len(self.tasks)} jobs to finish...")
            await asyncio.gather(*self.tasks, return_exceptions=True)
            
        async with AsyncSessionLocal() as session:
            stmt = update(Worker).where(Worker.id == self.worker_id).values(status="offline")
            await session.execute(stmt)
            await session.commit()
        print("Worker service stopped.")
