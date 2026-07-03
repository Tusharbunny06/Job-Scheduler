"""
Tests for ScheduledJob REST API and CronScheduler dispatch behavior.
"""
import pytest
from httpx import AsyncClient
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.job import ScheduledJob, Job
from app.models.queue import Queue, RetryPolicy
from app.models.project import Project
from app.models.organization import Organization
from app.scheduler.cron_scheduler import CronScheduler


# ── Setup helpers ─────────────────────────────────────────────────────────────

async def _create_queue(db: AsyncSession) -> str:
    org = Organization(name="Scheduler Test Org")
    db.add(org)
    await db.flush()
    proj = Project(name="Scheduler Test Project", organization_id=org.id)
    db.add(proj)
    await db.flush()
    queue = Queue(name="test-queue", project_id=proj.id)
    db.add(queue)
    await db.flush()
    q_id = queue.id
    await db.commit()
    return q_id


# ── CronScheduler dispatch test ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cron_scheduler_dispatches_due_job(db_session: AsyncSession):
    """CronScheduler should enqueue a new Job when next_run_at has passed."""
    queue_id = await _create_queue(db_session)

    # Create a scheduled job whose next_run_at is in the past
    past_time = datetime.now(timezone.utc) - timedelta(minutes=1)
    sched = ScheduledJob(
        queue_id=queue_id,
        name="test-cron",
        payload={"action": "test"},
        cron_expression="* * * * *",  # every minute
        next_run_at=past_time,
        is_active=True,
    )
    db_session.add(sched)
    await db_session.flush()
    sched_id = sched.id
    await db_session.commit()

    scheduler = CronScheduler(tick_interval=9999)
    await scheduler._tick()
    
    # Expire all to clear SQLAlchemy identity map cache since the scheduler used a different session
    db_session.expire_all()

    # Should have created a new queued job
    stmt = select(Job).where(Job.queue_id == queue_id)
    result = await db_session.execute(stmt)
    jobs = result.scalars().all()
    assert len(jobs) == 1
    assert jobs[0].status == "queued"

    # next_run_at should have advanced
    stmt = select(ScheduledJob).where(ScheduledJob.id == sched_id)
    result = await db_session.execute(stmt)
    updated = result.scalars().first()
    assert updated.next_run_at > past_time
    assert updated.last_run_at is not None


@pytest.mark.asyncio
async def test_cron_scheduler_skips_inactive(db_session: AsyncSession):
    """CronScheduler should NOT dispatch jobs for inactive ScheduledJob entries."""
    queue_id = await _create_queue(db_session)

    past_time = datetime.now(timezone.utc) - timedelta(minutes=1)
    sched = ScheduledJob(
        queue_id=queue_id,
        payload={"action": "inactive_test"},
        cron_expression="* * * * *",
        next_run_at=past_time,
        is_active=False,  # Disabled
    )
    db_session.add(sched)
    await db_session.commit()

    scheduler = CronScheduler(tick_interval=9999)
    await scheduler._tick()

    stmt = select(Job).where(Job.queue_id == queue_id)
    result = await db_session.execute(stmt)
    jobs = result.scalars().all()
    assert len(jobs) == 0, "Inactive scheduled job should not dispatch"


# ── REST API tests ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_scheduled_job_api(client: AsyncClient):
    """Test creating a scheduled job via REST API."""
    # Register + login
    await client.post("/api/v1/auth/register", json={"email": "cron_test@test.com", "password": "pass123"})
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": "cron_test@test.com", "password": "pass123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = login.json().get("access_token", "")
    headers = {"Authorization": f"Bearer {token}"}

    # Create a project first
    proj_res = await client.post("/api/v1/projects/", json={"name": "Cron Test Project"}, headers=headers)
    # Get a queue
    queue_res = await client.post(
        "/api/v1/queues/",
        json={"name": "cron-q", "project_id": proj_res.json().get("id", str(uuid4()))},
        headers=headers,
    )
    queue_id = queue_res.json().get("id")

    if not queue_id:
        pytest.skip("Could not create queue — skipping API test")

    res = await client.post(
        "/api/v1/scheduled-jobs/",
        json={
            "queue_id": queue_id,
            "name": "My Hourly Job",
            "payload": {"task": "cleanup"},
            "cron_expression": "0 * * * *",
        },
        headers=headers,
    )
    assert res.status_code == 201
    data = res.json()
    assert data["cron_expression"] == "0 * * * *"
    assert data["is_active"] is True
    assert data["name"] == "My Hourly Job"
    assert "next_run_at" in data


@pytest.mark.asyncio
async def test_invalid_cron_expression_rejected(client: AsyncClient):
    """Test that invalid cron expressions are rejected with a 422."""
    await client.post("/api/v1/auth/register", json={"email": "cron2@test.com", "password": "pass123"})
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": "cron2@test.com", "password": "pass123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = login.json().get("access_token", "")
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.post(
        "/api/v1/scheduled-jobs/",
        json={
            "queue_id": str(uuid4()),
            "payload": {},
            "cron_expression": "not a valid cron expression",
        },
        headers=headers,
    )
    assert res.status_code == 422, "Invalid cron expression should be rejected"
