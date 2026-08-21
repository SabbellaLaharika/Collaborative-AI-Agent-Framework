import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.db.models import TaskModel
from src.worker.tasks import run_agent_workflow, resume_agent_workflow
from src.api.schemas import (
    TaskCreateRequest,
    TaskCreateResponse,
    TaskResponse,
    TaskApproveRequest,
    TaskApproveResponse,
    HTTPError400Detail,
    HTTPError404Detail,
)

router = APIRouter(prefix="/api/v1/tasks", tags=["Tasks"])

@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=TaskCreateResponse,
    summary="Create Collaborative Agent Task",
    description="Initiates an asynchronous multi-agent research & writing task in Celery worker and immediately returns a PENDING task UUID (<500ms)."
)
def create_task(request: TaskCreateRequest, db: Session = Depends(get_db)):
    task_id = str(uuid.uuid4())
    
    new_task = TaskModel(
        id=uuid.UUID(task_id),
        prompt=request.prompt,
        status="PENDING",
        result=None,
        agent_logs=[]
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    run_agent_workflow.delay(task_id, request.prompt)

    return TaskCreateResponse(task_id=task_id, status="PENDING")

@router.get(
    "/{task_id}",
    status_code=status.HTTP_200_OK,
    response_model=TaskResponse,
    summary="Get Task Details & Audit Logs",
    description="Retrieves current status, research/writing result, and full agent_logs audit trail for a task.",
    responses={
        400: {"model": HTTPError400Detail, "description": "Invalid UUID format supplied"},
        404: {"model": HTTPError404Detail, "description": "Task not found in PostgreSQL database"},
    }
)
def get_task(task_id: str, db: Session = Depends(get_db)):
    try:
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid task_id format. Must be a valid UUID."
        )

    task = db.query(TaskModel).filter(TaskModel.id == task_uuid).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID '{task_id}' not found."
        )

    return TaskResponse(
        id=str(task.id),
        prompt=task.prompt,
        status=task.status,
        result=task.result,
        agent_logs=task.agent_logs,
        created_at=task.created_at.isoformat() if task.created_at else "",
        updated_at=task.updated_at.isoformat() if task.updated_at else ""
    )

@router.post(
    "/{task_id}/approve",
    status_code=status.HTTP_200_OK,
    response_model=TaskApproveResponse,
    summary="Human-in-the-Loop Task Approval",
    description="Resumes a workflow paused at AWAITING_APPROVAL checkpoint and dispatches completion task to Celery worker.",
    responses={
        400: {"model": HTTPError400Detail, "description": "Invalid UUID format supplied"},
        404: {"model": HTTPError404Detail, "description": "Task not found in PostgreSQL database"},
    }
)
def approve_task(
    task_id: str,
    request: TaskApproveRequest = TaskApproveRequest(),
    db: Session = Depends(get_db)
):
    try:
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid task_id format. Must be a valid UUID."
        )

    task = db.query(TaskModel).filter(TaskModel.id == task_uuid).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID '{task_id}' not found."
        )

    task.status = "RESUMED"
    db.commit()

    resume_agent_workflow.delay(task_id, request.approved, request.feedback or "")

    return TaskApproveResponse(task_id=task_id, status="RESUMED")
