from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.queue import Queue, RetryPolicy
from app.schemas.queue import QueueCreate, QueueUpdate
from typing import List, Optional
from uuid import UUID

class QueueRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, queue_id: UUID) -> Optional[Queue]:
        stmt = select(Queue).where(Queue.id == queue_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_all_by_project(self, project_id: UUID, skip: int = 0, limit: int = 100) -> List[Queue]:
        stmt = select(Queue).where(Queue.project_id == project_id).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Queue]:
        stmt = select(Queue).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, queue_in: QueueCreate) -> Queue:
        db_queue = Queue(
            project_id=queue_in.project_id,
            name=queue_in.name,
            priority=queue_in.priority,
            concurrency_limit=queue_in.concurrency_limit,
            is_paused=queue_in.is_paused
        )
        self.session.add(db_queue)
        await self.session.flush()
        
        if queue_in.retry_policy:
            db_retry_policy = RetryPolicy(
                queue_id=db_queue.id,
                max_retries=queue_in.retry_policy.max_retries,
                strategy=queue_in.retry_policy.strategy,
                delay_seconds=queue_in.retry_policy.delay_seconds,
                backoff_multiplier=queue_in.retry_policy.backoff_multiplier
            )
            self.session.add(db_retry_policy)
            
        await self.session.commit()
        await self.session.refresh(db_queue)
        return db_queue

    async def update(self, queue_id: UUID, queue_update: QueueUpdate) -> Optional[Queue]:
        queue = await self.get_by_id(queue_id)
        if not queue:
            return None
            
        update_data = queue_update.model_dump(exclude_unset=True, exclude={"retry_policy"})
        for field, value in update_data.items():
            setattr(queue, field, value)
            
        if queue_update.retry_policy:
            stmt = select(RetryPolicy).where(RetryPolicy.queue_id == queue_id)
            result = await self.session.execute(stmt)
            policy = result.scalars().first()
            if policy:
                policy.max_retries = queue_update.retry_policy.max_retries
                policy.strategy = queue_update.retry_policy.strategy
                policy.delay_seconds = queue_update.retry_policy.delay_seconds
                policy.backoff_multiplier = queue_update.retry_policy.backoff_multiplier
            else:
                new_policy = RetryPolicy(
                    queue_id=queue.id,
                    max_retries=queue_update.retry_policy.max_retries,
                    strategy=queue_update.retry_policy.strategy,
                    delay_seconds=queue_update.retry_policy.delay_seconds,
                    backoff_multiplier=queue_update.retry_policy.backoff_multiplier
                )
                self.session.add(new_policy)

        await self.session.commit()
        await self.session.refresh(queue)
        return queue

