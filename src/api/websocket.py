import json
import logging
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import redis.asyncio as aioredis
from src.config.settings import settings

logger = logging.getLogger(__name__)

ws_router = APIRouter(tags=["WebSockets"])

@ws_router.websocket("/ws/tasks/{task_id}")
async def websocket_task_status(websocket: WebSocket, task_id: str):
    """
    WebSocket endpoint providing real-time task status updates.
    Subscribes to Redis Pub/Sub channel task:<task_id>:status and streams JSON payload frames to client.
    Message format: {"task_id": "<uuid_string>", "status": "<new_status_string>"}
    """
    await websocket.accept()
    logger.info(f"WebSocket client connected for task {task_id}")

    redis_client = None
    pubsub = None
    try:
        redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        pubsub = redis_client.pubsub()
        channel_name = f"task:{task_id}:status"

        await pubsub.subscribe(channel_name)
        logger.info(f"Subscribed WebSocket to Redis channel '{channel_name}'")

        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message.get("type") == "message":
                data = message.get("data")
                if data:
                    try:
                        payload = json.loads(data) if isinstance(data, str) else data
                    except Exception:
                        payload = {"task_id": task_id, "status": str(data)}

                    await websocket.send_json(payload)

            await asyncio.sleep(0.1)

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected for task {task_id}")
    except Exception as e:
        logger.error(f"Error in WebSocket status streaming for task {task_id}: {e}")
    finally:
        if pubsub:
            await pubsub.unsubscribe()
            await pubsub.close()
        if redis_client:
            await redis_client.close()
