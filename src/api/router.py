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
)

router = APIRouter(prefix="/api/v1/tasks", tags=["Tasks"])

@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=TaskCreateResponse)
def create_task(request: TaskCreateRequest, db: Session = Depends(get_db)):
    """
    Creates a new collaborative agent task, stores PENDING state in DB,
    and dispatches Celery background worker asynchronously (<500ms).
    """
    task_id = str(uuid.uuid4())
    
    # 1. Save new task to DB with status PENDING
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

    # 2. Dispatch background worker task asynchronously
    run_agent_workflow.delay(task_id, request.prompt)

    # 3. Return 202 Accepted response immediately
    return TaskCreateResponse(task_id=task_id, status="PENDING")

@router.get("/{task_id}", status_code=status.HTTP_200_OK, response_model=TaskResponse)
def get_task(task_id: str, db: Session = Depends(get_db)):
    """
    Retrieves current task details, execution status, final result, and agent audit logs.
    """
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

@router.post("/{task_id}/approve", status_code=status.HTTP_200_OK, response_model=TaskApproveResponse)
def approve_task(
    task_id: str,
    request: TaskApproveRequest = TaskApproveRequest(),
    db: Session = Depends(get_db)
):
    """
    Provides human approval to resume a task paused at AWAITING_APPROVAL checkpoint.
    """
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

    # Update database status to RESUMED
    task.status = "RESUMED"
    db.commit()

    # Dispatch Celery worker resume task
    resume_agent_workflow.delay(task_id, request.approved, request.feedback or "")

    return TaskApproveResponse(task_id=task_id, status="RESUMED")
