from typing import Optional, Any
from pydantic import BaseModel, Field

class TaskCreateRequest(BaseModel):
    prompt: str = Field(..., description="Initial user prompt for the agent workflow", min_length=1)

class TaskCreateResponse(BaseModel):
    task_id: str
    status: str = "PENDING"

class TaskResponse(BaseModel):
    id: str
    prompt: str
    status: str
    result: Optional[str] = None
    agent_logs: Optional[Any] = None
    created_at: str
    updated_at: str

class TaskApproveRequest(BaseModel):
    approved: bool = True
    feedback: Optional[str] = ""

class TaskApproveResponse(BaseModel):
    task_id: str
    status: str = "RESUMED"
