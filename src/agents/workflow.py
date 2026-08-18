import logging
from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime, timezone
from langgraph.graph import StateGraph, END

from src.agents.tools import simulated_search_tool
from src.agents.workspace import write_to_workspace, read_from_workspace
from src.agents.logger import log_agent_activity

logger = logging.getLogger(__name__)

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

    # Write findings to ephemeral Redis scratchpad key task:<task_id>:workspace
    write_to_workspace(task_id, findings)
    log_agent_activity(task_id, "ResearchAgent", f"Saved research findings to Redis workspace key task:{task_id}:workspace")

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    new_log = {
        "agent": "ResearchAgent",
        "action": "Searching for LangGraph features",
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

    log_agent_activity(task_id, "WritingAgent", "Drafting comparison summary based on research findings")

    draft = (
        f"# Comparison Summary: LangGraph vs. CrewAI\n\n"
        f"**Task Prompt**: {prompt}\n\n"
        f"## Executive Summary\n"
        f"Both LangGraph and CrewAI are modern backend framework choices for building collaborative multi-agent systems.\n\n"
        f"## Key Differences\n"
        f"- **LangGraph**: Designed around explicit stateful cyclic graphs with fine-grained control, persistence checkpointers, and native Human-in-the-Loop approval breakpoints.\n"
        f"- **CrewAI**: Provides higher-level autonomous role abstractions (Crews, Agents, Tasks) for rapid multi-agent team delegation.\n\n"
        f"## Research Data\n{workspace_data}"
    )

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    new_log = {
        "agent": "WritingAgent",
        "action": "Drafting comparison summary",
        "timestamp": timestamp
    }

    current_logs = list(state.get("agent_logs") or [])
    current_logs.append(new_log)

    log_agent_activity(task_id, "WritingAgent", "Completed draft comparison summary. Pausing workflow for human approval.")

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

# Global agent graph instance
agent_graph = create_agent_graph()
