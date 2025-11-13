"""
LangGraph Agent v3.2 - Refactored (Modular Architecture)
Hanya berisi graph builder & compiler logic.
"""
import logging
from langgraph.graph import StateGraph, END

from app.services.redis_rate_limiter import rate_limiter
from app.services.chat_engine.agent_state import AgentState

# Import nodes
from app.services.chat_engine.nodes import (
    sanitize_input,
    load_full_history,
    manage_context_window,
    summarize_context,
    classify_intent,
    query_transform,
    retrieve_context,
    rerank_context,
    context_compression,
    agent_node,
    reflection_node,
    call_tools,
    extract_preferences_node,
    check_context_length,
    prune_and_summarize_node
)

# Import routers
from app.services.chat_engine.routers import (
    route_after_context_management,
    route_after_classify,
    route_after_agent,
    route_after_reflection,
    route_check_context
)

# Import checkpoint
from app.services.chat_engine.checkpoint import AsyncCompatibleRedisSaver

logger = logging.getLogger(__name__)


def build_langgraph_agent():
    """Membangun LangGraph Agent v3.2 (modular, interrupt-ready)."""
    redis_client = getattr(rate_limiter, "redis", None)
    
    # TEMPORARY FIX: Disable checkpointing
    checkpointer = None
    # if redis_client:
    #     try:
    #         checkpointer = AsyncCompatibleRedisSaver(redis_client=redis_client)
    #         logger.info("✅ Redis checkpointer berhasil diinisialisasi")
    #     except Exception as e:
    #         logger.warning(f"⚠️ Gagal inisialisasi Redis checkpointer: {e}")
    #         checkpointer = None
    
    workflow = StateGraph(AgentState)

    # 1️⃣ Tambahkan Semua Node
    workflow.add_node("sanitize_input", sanitize_input)
    workflow.add_node("load_full_history", load_full_history)
    workflow.add_node("manage_context_window", manage_context_window)
    workflow.add_node("summarize_context", summarize_context)
    workflow.add_node("classify_intent", classify_intent)
    workflow.add_node("query_transform", query_transform)
    workflow.add_node("retrieve_context", retrieve_context)
    workflow.add_node("rerank_context", rerank_context)
    workflow.add_node("context_compression", context_compression)
    workflow.add_node("agent_node", agent_node)
    workflow.add_node("reflection_node", reflection_node)
    workflow.add_node("call_tools", call_tools)
    workflow.add_node("extract_preferences_node", extract_preferences_node)
    workflow.add_node("check_context_length", check_context_length)
    workflow.add_node("prune_and_summarize_node", prune_and_summarize_node)

    # Interrupt node
    def interrupt_node(state: AgentState):
        """Menjeda graph sementara, menunggu aksi manusia (HiTL)."""
        logger.warning(f"Graph dijeda untuk request_id={state.get('request_id')}")
        return state
    workflow.add_node("interrupt", interrupt_node)

    # 2️⃣ Define Edges
    workflow.set_entry_point("sanitize_input")
    workflow.add_edge("sanitize_input", "load_full_history")
    workflow.add_edge("load_full_history", "manage_context_window")

    workflow.add_conditional_edges(
        "manage_context_window",
        route_after_context_management,
        {"summarize_context": "summarize_context", "classify_intent": "classify_intent"},
    )

    workflow.add_edge("summarize_context", "classify_intent")

    workflow.add_conditional_edges(
        "classify_intent",
        route_after_classify,
        {"query_transform": "query_transform", "agent_node": "agent_node", "__end__": END},
    )

    # RAG Flow
    workflow.add_edge("query_transform", "retrieve_context")
    workflow.add_edge("retrieve_context", "rerank_context")
    workflow.add_edge("rerank_context", "context_compression")
    workflow.add_edge("context_compression", "agent_node")

    workflow.add_conditional_edges(
        "agent_node",
        route_after_agent,
        {"reflection_node": "reflection_node", "extract_preferences_node": "extract_preferences_node", "__end__": END},
    )

    workflow.add_conditional_edges(
        "reflection_node",
        route_after_reflection,
        {"call_tools": "call_tools", "interrupt": "interrupt"},
    )

    workflow.add_edge("call_tools", "agent_node")
    workflow.add_edge("extract_preferences_node", "check_context_length")

    workflow.add_conditional_edges(
        "check_context_length",
        route_check_context,
        {"prune_and_summarize_node": "prune_and_summarize_node", "__end__": END},
    )
    workflow.add_edge("prune_and_summarize_node", END)

    # ✅ Kompilasi Graph
    logger.info("🔁 Mengkompilasi LangGraph Agent v3.2 (tanpa checkpointing)...")
    return workflow.compile()  # ← Remove checkpointer argument


compiled_langgraph_agent = build_langgraph_agent()

# Make sure this tool is exported:
from langchain_core.tools import tool

@tool
def create_schedule_tool(
    title: str,
    start_time: str,
    end_time: str = None,
    description: str = None
) -> str:
    """
    Membuat jadwal/event baru.
    
    Args:
        title: Judul event
        start_time: Waktu mulai (ISO format)
        end_time: Waktu selesai (optional)
        description: Deskripsi event (optional)
    
    Returns:
        str: Status pembuatan jadwal
    """
    # TODO: Implement actual schedule creation
    return f"Schedule '{title}' created successfully (stub implementation)"