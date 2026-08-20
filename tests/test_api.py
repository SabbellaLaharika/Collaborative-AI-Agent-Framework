import uuid
import pytest
from unittest.mock import patch

@pytest.mark.asyncio
async def test_health_check(async_client):
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@pytest.mark.asyncio
@patch("src.api.router.run_agent_workflow.delay")
async def test_create_task(mock_celery, async_client):
    prompt_text = "Research the key features of LangGraph and CrewAI."
    response = await async_client.post("/api/v1/tasks", json={"prompt": prompt_text})
    
    assert response.status_code == 202
    data = response.json()
    assert "task_id" in data
    assert data["status"] == "PENDING"
    mock_celery.assert_called_once()

@pytest.mark.asyncio
async def test_get_nonexistent_task(async_client):
    fake_uuid = str(uuid.uuid4())
    response = await async_client.get(f"/api/v1/tasks/{fake_uuid}")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_get_invalid_uuid_task(async_client):
    response = await async_client.get("/api/v1/tasks/invalid-uuid-format")
    assert response.status_code == 400
