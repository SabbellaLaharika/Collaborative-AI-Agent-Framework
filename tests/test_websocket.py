import json
import pytest
from src.api.websocket import ws_router

def test_websocket_router_registration():
    routes = [route.path for route in ws_router.routes]
    assert "/ws/tasks/{task_id}" in routes
