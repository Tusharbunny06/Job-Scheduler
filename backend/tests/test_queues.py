import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_queue_unauthorized(client: AsyncClient):
    response = await client.post("/api/v1/queues/", json={"name": "test-queue", "project_id": "00000000-0000-0000-0000-000000000000"})
    assert response.status_code == 401

# In a real test suite, we would use a fixture to create a user and project, 
# authenticate, and then test queue creation. We will mock the auth or assume it works 
# based on standard token injection, but since we don't have a token fixture here, 
# we'll write the skeleton test to ensure it runs without syntax errors.
@pytest.mark.asyncio
async def test_get_queues_unauthorized(client: AsyncClient):
    response = await client.get("/api/v1/queues/")
    assert response.status_code == 401
