import logging
from typing import Dict, Any, Optional, TYPE_CHECKING

from langchain_core.messages import SystemMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from opentelemetry import trace

from app.services.chat_engine.agent_state import AgentState
from app.services.chat_engine.llm_client import llm_pro_client
from app.services.chat_engine.agent_prompts import AGENT_SYSTEM_PROMPT

if TYPE_CHECKING:
    from app.services.chat_engine.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# Lazy initialization - avoid circular import
_tool_registry = None

def _get_tool_registry():
    """Lazy load tool registry to avoid circular import."""
    global _tool_registry
    if _tool_registry is None:
        from app.services.chat_engine.tools.registry import TOOL_REGISTRY_INSTANCE
        _tool_registry = TOOL_REGISTRY_INSTANCE
    return _tool_registry

def _count_tokens(text: str) -> int:
    """Estimasi token count."""
    if not text:
        return 0
    try:
        import tiktoken
        return len(tiktoken.get_encoding("cl100k_base").encode(text))
    except:
        return len(text) // 4


async def agent_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """Node #2: Agent utama dengan streaming."""
    request_id = state.get("request_id")
    logger.info(f"REQUEST_ID: {request_id} - Node: agent_node")
    
    with tracer.start_as_current_span("agent_node") as span:
        try:
            prompt = AGENT_SYSTEM_PROMPT.format(
                compressed_context=state.get("compressed_context", "(Tidak ada konteks RAG)"),
                chat_history=state.get("chat_history", []),
                user_message=state.get("user_message", "")
            )
            messages = [SystemMessage(content=prompt)] + state.get("chat_history", [])
            
            input_tokens = sum(_count_tokens(m.content) for m in messages if m.content)
            span.set_attribute("app.input_tokens", input_tokens)
            
            # TEMPORARY: Disable tools
            # tool_registry = _get_tool_registry()
            # llm_with_tools = llm_pro_client.get_llm().bind_tools(tool_registry.values())
            
            # Use LLM without tools
            llm_with_tools = llm_pro_client.get_llm()
            
            # DEBUG: Log sebelum streaming
            logger.debug(f"REQUEST_ID: {request_id} - Memulai streaming dari LLM...")
            
            stream = llm_with_tools.astream(messages, config=config)
            
            final_message: Optional[AIMessage] = None
            chunk_count = 0
            async for chunk in stream:
                chunk_count += 1
                if final_message is None:
                    final_message = chunk
                else:
                    final_message += chunk
            
            # DEBUG: Log hasil streaming
            logger.debug(f"REQUEST_ID: {request_id} - Streaming selesai. Chunks: {chunk_count}")
            logger.debug(f"REQUEST_ID: {request_id} - Final message type: {type(final_message)}")
            
            if final_message is None:
                logger.warning(f"REQUEST_ID: {request_id} - LLM tidak mengembalikan response. Menggunakan fallback.")
                final_message = AIMessage(content="Maaf, saya tidak dapat merespons saat ini. Silakan coba lagi.")

            # Pastikan final_message.content tidak None
            if not final_message.content:
                logger.warning(f"REQUEST_ID: {request_id} - Final message content kosong.")
                final_message.content = "Maaf, respons saya kosong. Silakan coba lagi dengan pertanyaan yang lebih spesifik."

            output_tokens = _count_tokens(final_message.content)
            cost = state.get("cost_estimate", 0.0)
            span.set_attributes({"app.output_tokens": output_tokens})
            
            logger.info(f"REQUEST_ID: {request_id} - Agent node selesai. Response length: {len(final_message.content)}")
            logger.debug(f"REQUEST_ID: {request_id} - Tokens - Input: {input_tokens}, Output: {output_tokens}")

            return {
                "chat_history": state.get("chat_history", []) + [final_message],
                "cost_estimate": cost,
                "output_token_count": state.get("output_token_count", 0) + output_tokens,
                "input_token_count": state.get("input_token_count", 0) + input_tokens,
                "api_call_count": state.get("api_call_count", 0) + 1,  # Increment
                "final_response": final_message.content
            }
        except Exception as e:
            logger.error(f"REQUEST_ID: {request_id} - Gagal di agent_node: {e}", exc_info=True)
            span.set_status(trace.StatusCode.ERROR, f"Error: {e}")
            error_message = f"Maaf, terjadi kesalahan: {str(e)}"
            return {
                "chat_history": state.get("chat_history", []) + [AIMessage(content=error_message)],
                "final_response": error_message,
                "errors": state.get("errors", []) + [{"node": "agent_node", "error": str(e)}]
            }
