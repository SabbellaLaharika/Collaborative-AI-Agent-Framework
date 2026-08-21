import os
import logging
from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime, timezone
from langgraph.graph import StateGraph, END

from src.agents.tools import simulated_search_tool
from src.agents.workspace import write_to_workspace, read_from_workspace
from src.agents.logger import log_agent_activity
from src.config.settings import settings

logger = logging.getLogger(__name__)

def get_llm():
    """
    Dynamically loads LLM provider configuration from environment variables (.env).
    Supports OpenAI, NVIDIA API (https://integrate.api.nvidia.com/v1), or any OpenAI-compatible provider.
    """
    api_key = settings.LLM_API_KEY or os.environ.get("LLM_API_KEY", "")
    invalid_prefixes = ("sk-your-provider", "nvapi-your-nvidia", "AQ.")
    if api_key and not any(api_key.startswith(prefix) for prefix in invalid_prefixes) and len(api_key) > 5:
        try:
            from langchain_openai import ChatOpenAI
            model_name = settings.LLM_MODEL or os.environ.get("LLM_MODEL", "gpt-3.5-turbo")
            kwargs: Dict[str, Any] = {
                "api_key": api_key,
                "model": model_name,
                "temperature": 0.7
            }
            base_url = settings.LLM_BASE_URL or os.environ.get("LLM_BASE_URL")
            if base_url:
                kwargs["base_url"] = base_url

            return ChatOpenAI(**kwargs)
        except Exception as e:
            logger.warning(f"Could not initialize ChatOpenAI: {e}")
            return None
    return None

class AgentState(TypedDict, total=False):
    task_id: str
    prompt: str
    research_findings: Optional[str]
    draft_summary: Optional[str]
    final_result: Optional[str]
    status: str
    agent_logs: List[Dict[str, Any]]
    approved: bool
    feedback: Optional[str]
    errors: List[str]

def research_node(state: AgentState) -> Dict[str, Any]:
    task_id = state.get("task_id", "unknown")
    prompt = state.get("prompt", "")

    log_agent_activity(task_id, "ResearchAgent", f"Starting research phase for prompt: '{prompt}'")
    
    query = prompt if prompt else "LangGraph and CrewAI features"
    search_output = simulated_search_tool(query, task_id=task_id)

    findings = f"Research Findings:\n{search_output}"

    write_to_workspace(task_id, findings)
    log_agent_activity(task_id, "ResearchAgent", f"Saved research findings to Redis workspace key task:{task_id}:workspace")

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    new_log = {
        "agent": "ResearchAgent",
        "action": f"Searching for '{query}'",
        "timestamp": timestamp
    }

    current_logs = list(state.get("agent_logs") or [])
    current_logs.append(new_log)

    return {
        "research_findings": findings,
        "agent_logs": current_logs,
        "status": "RUNNING"
    }

def writing_node(state: AgentState) -> Dict[str, Any]:
    task_id = state.get("task_id", "unknown")
    prompt = state.get("prompt", "")

    log_agent_activity(task_id, "WritingAgent", "Fetching research findings from Redis workspace")
    
    workspace_data = read_from_workspace(task_id)
    if not workspace_data:
        workspace_data = state.get("research_findings", "No research findings found.")

    log_agent_activity(task_id, "WritingAgent", f"Drafting summary for prompt: '{prompt}'")

    llm = get_llm()
    if llm:
        try:
            model_info = settings.LLM_MODEL or "dynamic-llm"
            log_agent_activity(task_id, "WritingAgent", f"Synthesizing summary via live LLM provider ({model_info})")
            response = llm.invoke(
                f"Task Prompt: {prompt}\n"
                f"Research Data:\n{workspace_data}\n\n"
                f"Write a cohesive, technical summary/response based on the prompt and research data."
            )
            draft = response.content if hasattr(response, "content") else str(response)
        except Exception as e:
            logger.warning(f"LLM invocation failed, using fallback summary generator: {e}")
            llm = None

    if not llm:
        draft = (
            f"# Technical Report: {prompt}\n\n"
            f"**Task Prompt**: {prompt}\n\n"
            f"## Executive Summary\n"
            f"This summary synthesizes technical research findings for: '{prompt}'.\n\n"
            f"## Key Architectural & Feature Analysis\n"
            f"{workspace_data}\n\n"
            f"## Conclusion\n"
            f"Evaluated criteria for '{prompt}' successfully. The workflow completed state transitions and is ready for final deployment."
        )

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    new_log = {
        "agent": "WritingAgent",
        "action": f"Drafting summary for '{prompt}'",
        "timestamp": timestamp
    }

    current_logs = list(state.get("agent_logs") or [])
    current_logs.append(new_log)

    log_agent_activity(task_id, "WritingAgent", "Completed draft summary. Pausing workflow for human approval.")

    return {
        "draft_summary": draft,
        "agent_logs": current_logs,
        "status": "AWAITING_APPROVAL"
    }

def approval_node(state: AgentState) -> Dict[str, Any]:
    task_id = state.get("task_id", "unknown")
    approved = state.get("approved", False)
    draft = state.get("draft_summary", "")
    feedback = state.get("feedback", "")

    if approved:
        log_agent_activity(task_id, "WorkflowOrchestrator", f"Human approval granted. Feedback: '{feedback}'")
        final_text = draft
        if feedback:
            final_text += f"\n\n### Human Feedback\n{feedback}"

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        new_log = {
            "agent": "WorkflowOrchestrator",
            "action": "Task approved by human operator. Completed workflow.",
            "timestamp": timestamp
        }

        current_logs = list(state.get("agent_logs") or [])
        current_logs.append(new_log)

        return {
            "final_result": final_text,
            "status": "COMPLETED",
            "agent_logs": current_logs
        }
    else:
        log_agent_activity(task_id, "WorkflowOrchestrator", "Workflow paused at Human Approval Gate: awaiting approval")
        return {
            "status": "AWAITING_APPROVAL"
        }

def create_agent_graph():
    """Compiles and returns the LangGraph workflow graph."""
    workflow = StateGraph(AgentState)

    workflow.add_node("research", research_node)
    workflow.add_node("writing", writing_node)
    workflow.add_node("approval", approval_node)

    workflow.set_entry_point("research")
    workflow.add_edge("research", "writing")
    workflow.add_edge("writing", "approval")
    workflow.add_edge("approval", END)

    return workflow.compile()

agent_graph = create_agent_graph()
