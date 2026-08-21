from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict

class TaskCreateRequest(BaseModel):
    prompt: str = Field(
        ...,
        description="Initial prompt instructing the collaborative agent workflow",
        min_length=1
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "prompt": "Research the key features of LangGraph and CrewAI. Write a short comparison summary for a technical audience."
            }
        }
    )

class TaskCreateResponse(BaseModel):
    task_id: str = Field(..., description="Unique UUID string identifying the created task workflow")
    status: str = Field("PENDING", description="Initial task creation status")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "task_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "PENDING"
            }
        }
    )

class TaskResponse(BaseModel):
    id: str = Field(..., description="Unique task UUID string")
    prompt: str = Field(..., description="User prompt supplied at creation")
    status: str = Field(..., description="Current status of workflow (PENDING, RUNNING, AWAITING_APPROVAL, RESUMED, COMPLETED, FAILED)")
    result: Optional[str] = Field(None, description="Final comparison result produced by agents upon completion")
    agent_logs: Optional[Any] = Field(None, description="Structured audit array detailing agent steps and timestamps")
    created_at: str = Field(..., description="ISO 8601 timestamp of task creation")
    updated_at: str = Field(..., description="ISO 8601 timestamp of last task update")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "prompt": "Research the key features of LangGraph and CrewAI. Write a short comparison summary for a technical audience.",
                "status": "AWAITING_APPROVAL",
                "result": None,
                "agent_logs": [
                    {
                        "agent": "ResearchAgent",
                        "action": "Searching for LangGraph features",
                        "timestamp": "2026-08-21T14:00:00Z"
                    },
                    {
                        "agent": "WritingAgent",
                        "action": "Drafting comparison summary",
                        "timestamp": "2026-08-21T14:01:15Z"
                    }
                ],
                "created_at": "2026-08-21T14:00:00Z",
                "updated_at": "2026-08-21T14:01:15Z"
            }
        }
    )

class TaskApproveRequest(BaseModel):
    approved: bool = Field(True, description="Flag indicating human approval decision")
    feedback: Optional[str] = Field("", description="Optional feedback or instructions from human operator")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "approved": True,
                "feedback": "Looks great, proceed with finalizing summary!"
            }
        }
    )

class TaskApproveResponse(BaseModel):
    task_id: str = Field(..., description="Unique UUID identifying approved task")
    status: str = Field("RESUMED", description="Updated task status indicating workflow resumption")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "task_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "RESUMED"
            }
        }
    )

class HTTPError400Detail(BaseModel):
    detail: str = Field(..., description="Bad request error message")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "detail": "Invalid task_id format. Must be a valid UUID."
            }
        }
    )

class HTTPError404Detail(BaseModel):
    detail: str = Field(..., description="Resource not found error message")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "detail": "Task with ID '123e4567-e89b-12d3-a456-426614174000' not found."
            }
        }
    )
