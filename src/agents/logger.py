import json
import os
from datetime import datetime, timezone

LOG_FILE_PATH = os.path.join(os.getcwd(), "logs", "agent_activity.log")

def log_agent_activity(task_id: str, agent_name: str, action_details: str) -> None:
    """
    Appends a structured JSON object to logs/agent_activity.log.
    Each line must be an independent JSON object formatted as:
    {"timestamp": "2023-10-27T10:00:05.123Z", "task_id": "...", "agent_name": "...", "action_details": "..."}
    """
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    log_entry = {
        "timestamp": now_str,
        "task_id": str(task_id),
        "agent_name": agent_name,
        "action_details": action_details
    }
    
    os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)
    
    with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")
