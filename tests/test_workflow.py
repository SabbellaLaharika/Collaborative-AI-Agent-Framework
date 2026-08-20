import json
import pytest
from src.agents.workflow import create_agent_graph
from src.agents.tools import simulated_search_tool, flaky_tool_attempts
from src.agents.workspace import get_workspace_key
from src.agents.logger import log_agent_activity, LOG_FILE_PATH

def test_graph_compilation():
    graph = create_agent_graph()
    assert graph is not None

def test_flaky_tool_retry():
    query = "__FLAKY_TEST__"
    task_id = "test-flaky-retry-task"
    
    # Reset attempt tracker
    flaky_tool_attempts.clear()

    # Calling simulated_search_tool equipped with @retry
    result = simulated_search_tool(query, task_id=task_id)
    assert "second attempt" in result

def test_workspace_key_format():
    task_id = "123e4567-e89b-12d3-a456-426614174000"
    key = get_workspace_key(task_id)
    assert key == f"task:{task_id}:workspace"

def test_structured_agent_activity_logger(tmp_path, monkeypatch):
    test_log_file = tmp_path / "agent_activity.log"
    monkeypatch.setattr("src.agents.logger.LOG_FILE_PATH", str(test_log_file))

    task_id = "test-log-uuid"
    log_agent_activity(task_id, "ResearchAgent", "Searching for LangGraph features")

    assert test_log_file.exists()
    line = test_log_file.read_text(encoding="utf-8").strip()
    entry = json.loads(line)

    assert entry["task_id"] == task_id
    assert entry["agent_name"] == "ResearchAgent"
    assert entry["action_details"] == "Searching for LangGraph features"
    assert "timestamp" in entry
