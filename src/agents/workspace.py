import json
import logging
from typing import Any, Optional
from src.config.redis_client import get_redis_client

logger = logging.getLogger(__name__)

def get_workspace_key(task_id: str) -> str:
    """Generates standard key pattern task:<task_id>:workspace."""
    return f"task:{task_id}:workspace"

def write_to_workspace(task_id: str, data: Any) -> bool:
    """
    Writes intermediate agent findings/data to Redis workspace key task:<task_id>:workspace.
    """
    try:
        client = get_redis_client()
        key = get_workspace_key(task_id)
        if isinstance(data, (dict, list)):
            serialized = json.dumps(data)
        else:
            serialized = str(data)
        client.set(key, serialized)
        return True
    except Exception as e:
        logger.error(f"Failed to write to Redis workspace for task {task_id}: {e}")
        return False

def read_from_workspace(task_id: str) -> Optional[Any]:
    """
    Reads intermediate findings from Redis workspace key task:<task_id>:workspace.
    """
    try:
        client = get_redis_client()
        key = get_workspace_key(task_id)
        raw_val = client.get(key)
        if raw_val is None:
            return None
        try:
            return json.loads(raw_val)
        except Exception:
            return raw_val
    except Exception as e:
        logger.error(f"Failed to read from Redis workspace for task {task_id}: {e}")
        return None

def clear_workspace(task_id: str) -> bool:
    """
    Clears the Redis workspace key task:<task_id>:workspace.
    """
    try:
        client = get_redis_client()
        key = get_workspace_key(task_id)
        client.delete(key)
        return True
    except Exception as e:
        logger.error(f"Failed to clear Redis workspace for task {task_id}: {e}")
        return False

def publish_task_status(task_id: str, status: str) -> bool:
    """
    Publishes real-time task status update to Redis Pub/Sub channel task:<task_id>:status.
    Format: {"task_id": "<uuid_string>", "status": "<new_status_string>"}
    """
    try:
        client = get_redis_client()
        channel = f"task:{task_id}:status"
        payload = json.dumps({"task_id": str(task_id), "status": status})
        client.publish(channel, payload)
        return True
    except Exception as e:
        logger.error(f"Failed to publish task status via Redis Pub/Sub for task {task_id}: {e}")
        return False
