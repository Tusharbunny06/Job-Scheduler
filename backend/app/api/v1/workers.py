"""
Workers API — List workers and allow heartbeat via REST.
Worker registration happens within the worker process itself via direct DB writes.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import Annotated, List, Dict, Any
from uuid import UUID
from datetime import datetime, timezone, timedelta

from app.database.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.worker import Worker

router = APIRouter()


@router.get(
    "/",
    summary="List all registered workers",
    description=(
        "Returns all workers with their status, concurrency limit, and last heartbeat. "
        "Workers with heartbeat older than 2 minutes are flagged as stale."
    ),
)
async def list_workers(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> List[Dict[str, Any]]:
    stmt = select(Worker).order_by(Worker.last_heartbeat.desc())
    result = await db.execute(stmt)
    workers = result.scalars().all()

    two_mins_ago = datetime.now(timezone.utc) - timedelta(minutes=2)

    return [
        {
            "id": str(w.id),
            "hostname": w.hostname,
            "status": w.status,
            "concurrency_limit": w.concurrency_limit,
            "registered_at": w.registered_at.isoformat() if w.registered_at else None,
            "last_heartbeat": w.last_heartbeat.isoformat() if w.last_heartbeat else None,
            "is_stale": (
                w.last_heartbeat is None
                or w.last_heartbeat.replace(tzinfo=timezone.utc) < two_mins_ago
            ),
        }
        for w in workers
    ]


@router.get(
    "/{worker_id}",
    summary="Get a specific worker",
)
async def get_worker(
    worker_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Dict[str, Any]:
    stmt = select(Worker).where(Worker.id == worker_id)
    result = await db.execute(stmt)
    worker = result.scalars().first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    two_mins_ago = datetime.now(timezone.utc) - timedelta(minutes=2)
    return {
        "id": str(worker.id),
        "hostname": worker.hostname,
        "status": worker.status,
        "concurrency_limit": worker.concurrency_limit,
        "registered_at": worker.registered_at.isoformat() if worker.registered_at else None,
        "last_heartbeat": worker.last_heartbeat.isoformat() if worker.last_heartbeat else None,
        "is_stale": (
            worker.last_heartbeat is None
            or worker.last_heartbeat.replace(tzinfo=timezone.utc) < two_mins_ago
        ),
    }


@router.post(
    "/{worker_id}/heartbeat",
    summary="Update worker heartbeat via REST",
    description=(
        "Allows a worker to update its heartbeat via HTTP POST instead of direct DB write. "
        "Useful for workers in containerized or serverless environments."
    ),
)
async def worker_heartbeat(
    worker_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Dict[str, Any]:
    stmt = select(Worker).where(Worker.id == worker_id)
    result = await db.execute(stmt)
    worker = result.scalars().first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    now = datetime.now(timezone.utc)
    await db.execute(
        update(Worker).where(Worker.id == worker_id).values(last_heartbeat=now)
    )
    await db.commit()
    return {"status": "ok", "heartbeat_at": now.isoformat()}
