import uuid
import logging
from src.worker.celery_app import celery_app
from src.db.session import SessionLocal
from src.db.models import TaskModel
from src.agents.workflow import agent_graph, AgentState
from src.agents.workspace import publish_task_status, read_from_workspace
from src.agents.logger import log_agent_activity

logger = logging.getLogger(__name__)

@celery_app.task(name="src.worker.tasks.run_agent_workflow")
def run_agent_workflow(task_id: str, prompt: str):
    """
    Executes the initial research and writing stages of the LangGraph multi-agent workflow.
    Updates DB status to RUNNING -> AWAITING_APPROVAL and publishes status via Pub/Sub.
    """
    db = SessionLocal()
    try:
        task_uuid = uuid.UUID(task_id) if isinstance(task_id, str) else task_id
        db_task = db.query(TaskModel).filter(TaskModel.id == task_uuid).first()
        if db_task:
            db_task.status = "RUNNING"
            db.commit()

        publish_task_status(task_id, "RUNNING")
        log_agent_activity(task_id, "CeleryWorker", f"Dispatched task workflow execution for prompt: '{prompt}'")

        initial_state: AgentState = {
            "task_id": str(task_id),
            "prompt": prompt,
            "agent_logs": [],
            "approved": False,
            "status": "RUNNING"
        }

        output_state = agent_graph.invoke(initial_state)

        db_task = db.query(TaskModel).filter(TaskModel.id == task_uuid).first()
        if db_task:
            db_task.status = "AWAITING_APPROVAL"
            db_task.agent_logs = output_state.get("agent_logs", [])
            db.commit()

        publish_task_status(task_id, "AWAITING_APPROVAL")
        log_agent_activity(task_id, "CeleryWorker", "Completed research & writing phases. Workflow status set to AWAITING_APPROVAL.")

        return {
            "task_id": str(task_id),
            "status": "AWAITING_APPROVAL",
            "agent_logs": output_state.get("agent_logs", [])
        }
    except Exception as e:
        logger.error(f"Error executing agent workflow for task {task_id}: {e}")
        log_agent_activity(task_id, "CeleryWorker", f"Execution error in run_agent_workflow: {str(e)}")
        if db:
            task_uuid = uuid.UUID(task_id) if isinstance(task_id, str) else task_id
            db_task = db.query(TaskModel).filter(TaskModel.id == task_uuid).first()
            if db_task:
                db_task.status = "FAILED"
                db.commit()
        publish_task_status(task_id, "FAILED")
        raise e
    finally:
        db.close()

@celery_app.task(name="src.worker.tasks.resume_agent_workflow")
def resume_agent_workflow(task_id: str, approved: bool = True, feedback: str = ""):
    """
    Resumes the LangGraph multi-agent workflow from checkpoint upon human approval.
    Updates DB status to RESUMED -> COMPLETED and publishes status via Pub/Sub.
    """
    db = SessionLocal()
    try:
        task_uuid = uuid.UUID(task_id) if isinstance(task_id, str) else task_id
        db_task = db.query(TaskModel).filter(TaskModel.id == task_uuid).first()
        
        if not db_task:
            logger.error(f"Task {task_id} not found in database.")
            return

        db_task.status = "RESUMED"
        db.commit()

        publish_task_status(task_id, "RESUMED")
        log_agent_activity(task_id, "CeleryWorker", f"Workflow resumed with approved={approved}, feedback='{feedback}'")

        prompt = db_task.prompt
        existing_logs = db_task.agent_logs or []
        research_findings = read_from_workspace(task_id) or "LangGraph vs CrewAI research data"

        resume_state: AgentState = {
            "task_id": str(task_id),
            "prompt": prompt,
            "research_findings": str(research_findings),
            "agent_logs": existing_logs,
            "approved": approved,
            "feedback": feedback,
            "status": "RESUMED"
        }

        output_state = agent_graph.invoke(resume_state)

        final_status = output_state.get("status", "COMPLETED")
        final_result = output_state.get("final_result", output_state.get("draft_summary", ""))

        db_task = db.query(TaskModel).filter(TaskModel.id == task_uuid).first()
        if db_task:
            db_task.status = final_status
            db_task.result = final_result
            db_task.agent_logs = output_state.get("agent_logs", existing_logs)
            db.commit()

        publish_task_status(task_id, final_status)
        log_agent_activity(task_id, "CeleryWorker", f"Workflow finalized with status {final_status}. Result saved to database.")

        return {
            "task_id": str(task_id),
            "status": final_status,
            "result": final_result
        }
    except Exception as e:
        logger.error(f"Error resuming agent workflow for task {task_id}: {e}")
        log_agent_activity(task_id, "CeleryWorker", f"Execution error in resume_agent_workflow: {str(e)}")
        if db:
            task_uuid = uuid.UUID(task_id) if isinstance(task_id, str) else task_id
            db_task = db.query(TaskModel).filter(TaskModel.id == task_uuid).first()
            if db_task:
                db_task.status = "FAILED"
                db.commit()
        publish_task_status(task_id, "FAILED")
        raise e
    finally:
        db.close()
