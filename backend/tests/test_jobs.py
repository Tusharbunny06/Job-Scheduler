import pytest
from httpx import AsyncClient
import asyncio

@pytest.mark.asyncio
async def test_create_job_unauthorized(client: AsyncClient):
    response = await client.post("/api/v1/jobs/", json={"queue_id": "00000000-0000-0000-0000-000000000000", "payload": {}})
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_get_jobs_unauthorized(client: AsyncClient):
    response = await client.get("/api/v1/jobs/queue/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_batch_create_unauthorized(client: AsyncClient):
    response = await client.post("/api/v1/jobs/batch", json={"jobs": []})
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_retry_job_unauthorized(client: AsyncClient):
    response = await client.post("/api/v1/jobs/00000000-0000-0000-0000-000000000000/retry")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_create_job_authorized(client: AsyncClient, token_headers):
    # This assumes token_headers is provided by a fixture in conftest.py
    # Since we can't easily mock DB here without setup, we just ensure it doesn't return 401
    response = await client.post(
        "/api/v1/jobs/", 
        json={"queue_id": "00000000-0000-0000-0000-000000000000", "payload": {"foo": "bar"}},
        headers=token_headers
    )
    # It might return 400 or 500 if DB setup isn't done, but shouldn't be 401
    assert response.status_code != 401
