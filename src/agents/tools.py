import logging
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from src.agents.logger import log_agent_activity

logger = logging.getLogger(__name__)

# Dictionary tracking attempts for flaky tool simulation
flaky_tool_attempts = {}

def simulated_search_tool_raw(query: str, task_id: str = "unknown") -> str:
    """
    Simulated search tool.
    If query == '__FLAKY_TEST__', raises Exception on 1st attempt, succeeds on 2nd attempt.
    Dynamically generates research findings for any custom user query.
    """
    if query == "__FLAKY_TEST__":
        attempts = flaky_tool_attempts.get(query, 0)
        if attempts == 0:
            flaky_tool_attempts[query] = 1
            log_agent_activity(
                task_id,
                "ResearchAgent",
                f"Tool error on search query '{query}': Simulated transient network timeout."
            )
            raise Exception("Simulated transient network timeout.")
        
        log_agent_activity(
            task_id,
            "ResearchAgent",
            f"Retried search query '{query}' successfully on second attempt."
        )
        return "Search results retrieved on second attempt for __FLAKY_TEST__."

    # Dynamic response tailored to user's query
    if "langgraph" in query.lower() or "crewai" in query.lower():
        return (
            "LangGraph Features: Stateful multi-agent orchestration, cyclical graph routing, "
            "built-in Human-in-the-Loop breakpoints, persistence, fine-grained control over node transitions.\n"
            "CrewAI Features: Role-based autonomous agent collaboration, pre-built agent delegations, "
            "task-driven sequential/hierarchical execution, high-level prompt abstraction."
        )

    return (
        f"Research Results for '{query}':\n"
        f"- Core Concepts: Analyzed key architecture and underlying design principles for '{query}'.\n"
        f"- Performance & Scalability: High efficiency for distributed asynchronous execution.\n"
        f"- Integration Surface: Standard REST API, WebSocket streams, and structured logging capabilities."
    )

@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(0.1),
    retry=retry_if_exception_type(Exception),
    reraise=True
)
def simulated_search_tool(query: str, task_id: str = "unknown") -> str:
    """Simulated search tool equipped with automatic retry logic."""
    log_agent_activity(task_id, "ResearchAgent", f"Executing web search tool for query: '{query}'")
    return simulated_search_tool_raw(query, task_id=task_id)
