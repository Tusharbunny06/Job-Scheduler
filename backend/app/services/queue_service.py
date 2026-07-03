"""
Queue Service — business logic for queue operations.
"""
from typing import Dict
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.job import Job


class QueueService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_stats(self, queue_id: UUID) -> Dict[str, int]:
        """
        Return per-status job counts for a queue.
        Used for dashboard queue health visualization.
        """
        stmt = (
            select(Job.status, func.count(Job.id).label("count"))
            .where(Job.queue_id == queue_id)
            .group_by(Job.status)
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        # Initialize all known statuses to 0 for consistent response shape
        stats: Dict[str, int] = {
            "queued": 0,
            "scheduled": 0,
            "claimed": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
            "dlq": 0,
        }
        for row in rows:
            stats[row.status] = row.count

        stats["total"] = sum(stats.values())
        return stats
