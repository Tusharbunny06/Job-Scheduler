"""
Queues API — Create, read, update, delete queues and fetch per-queue statistics.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, Dict, List
from uuid import UUID

from app.database.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.queue import QueueCreate, QueueUpdate, QueueResponse
from app.repositories.queue_repository import QueueRepository
from app.services.queue_service import QueueService

router = APIRouter()


@router.get(
    "/",
    response_model=List[QueueResponse],
    summary="List all queues",
)
async def list_all_queues(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = QueueRepository(db)
    return await repo.get_all(skip=skip, limit=limit)


@router.post(
    "/",
    response_model=QueueResponse,
    status_code=201,
    summary="Create a queue",
    description="Creates a new job queue with optional retry policy. Queues belong to a project.",
)
async def create_queue(
    queue_in: QueueCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    repo = QueueRepository(db)
    return await repo.create(queue_in=queue_in)


@router.get(
    "/project/{project_id}",
    response_model=List[QueueResponse],
    summary="List queues by project",
)
async def list_queues_by_project(
    project_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = QueueRepository(db)
    return await repo.get_all_by_project(project_id=project_id, skip=skip, limit=limit)


@router.get(
    "/{queue_id}",
    response_model=QueueResponse,
    summary="Get queue details",
)
async def get_queue(
    queue_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = QueueRepository(db)
    queue = await repo.get_by_id(queue_id)
    if not queue:
        raise HTTPException(status_code=404, detail="Queue not found")
    return queue


@router.patch(
    "/{queue_id}",
    response_model=QueueResponse,
    summary="Update queue configuration",
    description="Update name, priority, concurrency limit, or pause/resume the queue.",
)
async def update_queue(
    queue_id: UUID,
    queue_update: QueueUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    repo = QueueRepository(db)
    queue = await repo.update(queue_id=queue_id, queue_update=queue_update)
    if not queue:
        raise HTTPException(status_code=404, detail="Queue not found")
    return queue


@router.delete(
    "/{queue_id}",
    status_code=204,
    summary="Delete a queue",
    description="Deletes the queue and all its associated jobs (CASCADE). This action is irreversible.",
)
async def delete_queue(
    queue_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    repo = QueueRepository(db)
    queue = await repo.get_by_id(queue_id)
    if not queue:
        raise HTTPException(status_code=404, detail="Queue not found")
    await db.delete(queue)
    await db.commit()


@router.get(
    "/{queue_id}/stats",
    response_model=Dict[str, int],
    summary="Get per-queue job statistics",
    description="Returns job counts grouped by status for the given queue. Used for dashboard health visualization.",
)
async def get_queue_stats(
    queue_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = QueueRepository(db)
    queue = await repo.get_by_id(queue_id)
    if not queue:
        raise HTTPException(status_code=404, detail="Queue not found")
    service = QueueService(db)
    return await service.get_stats(queue_id)
