"""
Fungsi routing untuk conditional edges di LangGraph.
"""
import logging
from langchain_core.messages import AIMessage
from app.services.chat_engine.agent_state import AgentState

logger = logging.getLogger(__name__)

CONTEXT_WINDOW_TOKEN_LIMIT = 8000


def route_after_context_management(state: AgentState) -> str:
    """Router setelah manage_context_window."""
    if state.get("messages_to_summarize"):
        return "summarize_context"
    return "classify_intent"


def route_after_classify(state: AgentState) -> str:
    """Router setelah classify_intent."""
    if state.get("errors"):
        return "__end__"
    intent = state.get("intent")
    return "query_transform" if intent == "rag_query" else "agent_node"


def route_after_agent(state: AgentState) -> str:
    """Router setelah agent_node."""
    if state.get("errors"):
        return "__end__"
    last_message = state["chat_history"][-1]
    return (
        "reflection_node"
        if isinstance(last_message, AIMessage) and getattr(last_message, "tool_calls", None)
        else "extract_preferences_node"
    )


def route_after_reflection(state: AgentState) -> str:
    """Router setelah reflection_node (HiTL)."""
    if state.get("errors"):
        return "__end__"
    if state.get("tool_approval_request"):
        logger.warning(f"REQUEST_ID={state.get('request_id')} → Graph dijeda menunggu persetujuan.")
        return "interrupt"
    else:
        return "call_tools"


def route_check_context(state: AgentState) -> str:
    """Router setelah check_context_length."""
    return (
        "prune_and_summarize_node"
        if state.get("total_tokens", 0) > CONTEXT_WINDOW_TOKEN_LIMIT
        else "__end__"
    )
