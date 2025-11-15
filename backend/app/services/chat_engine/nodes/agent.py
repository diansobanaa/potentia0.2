import logging
from typing import Dict, Any, Optional, TYPE_CHECKING
import datetime  # <-- [TAMBAHKAN]
import pytz      # <-- [TAMBAHKAN]

from langchain_core.messages import SystemMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from opentelemetry import trace

from app.services.chat_engine.agent_state import AgentState
from app.services.chat_engine.llm_client import llm_pro_client
from app.services.chat_engine.agent_prompts import AGENT_SYSTEM_PROMPT
from app.core.config import settings
from app.services.chat_engine.llm_provider import (
    get_chat_model,
    get_provider_from_model
)

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
    
    # Debug: Log full config structure
    logger.debug(
        f"REQUEST_ID: {request_id} - Received config type: {type(config)}"
    )
    logger.debug(
        f"REQUEST_ID: {request_id} - Has configurable attr: "
        f"{hasattr(config, 'configurable')}"
    )
    if hasattr(config, "configurable"):
        logger.debug(
            f"REQUEST_ID: {request_id} - config.configurable keys: "
            f"{list(config.configurable.keys()) if config.configurable else 'None'}"
        )
    
    with tracer.start_as_current_span("agent_node") as span:
        try:
            # --- [PERUBAHAN DIMULAI DI SINI] ---
            # 1. Dapatkan Waktu Saat Ini (Zona: Asia/Jakarta)
            try:
                user_timezone = pytz.timezone("Asia/Jakarta")
                now_utc = datetime.datetime.now(pytz.UTC)
                now_user_tz = now_utc.astimezone(user_timezone)
                current_time_str = f"Informasi Waktu: Waktu saat ini adalah {now_user_tz.strftime('%A, %Y-%m-%d %H:%M %Z')}."
            except Exception:
                current_time_str = "Informasi Waktu: Waktu saat ini tidak dapat ditentukan."
            
            # 2. Format prompt dengan 'current_time'
            prompt = AGENT_SYSTEM_PROMPT.format(
                current_time=current_time_str,
                compressed_context=state.get("compressed_context", "(Tidak ada konteks RAG)"),
                chat_history=state.get("chat_history", []),
                user_message=state.get("user_message", "")
            )
            # --- [PERUBAHAN SELESAI] ---

            messages = [SystemMessage(content=prompt)] + state.get("chat_history", [])
            input_tokens = sum(_count_tokens(m.content) for m in messages if getattr(m, "content", None))
            span.set_attribute("app.input_tokens", input_tokens)

            # Get LLM config from STATE (reliable way for LangGraph)
            model = state.get("llm_model") or settings.DEFAULT_MODEL
            temperature = state.get("llm_temperature") or settings.DEFAULT_TEMPERATURE
            max_tokens = state.get("llm_max_tokens")
            
            # Log what we extracted from state
            logger.info(
                f"🤖 agent_node using model from STATE: "
                f"model={model}, temp={temperature}, max_tokens={max_tokens}"
            )
            logger.debug(
                f"REQUEST_ID: {request_id} - LLM config from state: "
                f"model={model}, temp={temperature}, max_tokens={max_tokens}"
            )

            # Use factory to build LLM with all params
            llm = get_chat_model(
                model=model, 
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Check if fallback occurred and track it in state
            fallback_error = getattr(llm, "_fallback_error", None)
            if fallback_error:
                logger.warning(
                    f"REQUEST_ID: {request_id} - LLM fallback occurred: "
                    f"{fallback_error['original_model']} -> {settings.DEFAULT_MODEL}"
                )
                state["llm_fallback_error"] = fallback_error

            logger.info(
                f"✅ agent_node created LLM instance: model={model}, "
                f"temp={temperature}"
            )
            
            # Try streaming with the primary model
            final_message: Optional[AIMessage] = None
            chunk_count = 0
            
            try:
                stream = llm.astream(messages, config=config)
                async for chunk in stream:
                    chunk_count += 1
                    if final_message is None:
                        final_message = chunk
                    else:
                        final_message += chunk
            except Exception as stream_error:
                # Streaming failed - check if we should fallback
                error_str = str(stream_error)
                is_api_error = (
                    "429" in error_str or
                    "503" in error_str or
                    "quota" in error_str.lower() or
                    "rate limit" in error_str.lower() or
                    "suspended" in error_str.lower() or
                    "overloaded" in error_str.lower() or
                    "unavailable" in error_str.lower() or
                    "401" in error_str.lower() or
                    "unauthorized" in error_str.lower()
                )
                
                if is_api_error and model != settings.DEFAULT_MODEL:
                    logger.warning(
                        f"REQUEST_ID: {request_id} - Streaming failed with "
                        f"{model}, falling back to {settings.DEFAULT_MODEL}"
                    )
                    logger.warning(f"REQUEST_ID: {request_id} - Error: {error_str}")
                    
                    # Track fallback error
                    state["llm_fallback_error"] = {
                        "original_model": model,
                        "original_provider": get_provider_from_model(model),
                        "error": error_str
                    }
                    
                    # Fallback to Gemini (already imported at top)
                    fallback_llm = get_chat_model(
                        model=settings.DEFAULT_MODEL,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                    
                    logger.info(
                        f"REQUEST_ID: {request_id} - Retrying with fallback "
                        f"model: {settings.DEFAULT_MODEL}"
                    )
                    
                    # Retry with fallback
                    stream = fallback_llm.astream(messages, config=config)
                    async for chunk in stream:
                        chunk_count += 1
                        if final_message is None:
                            final_message = chunk
                        else:
                            final_message += chunk
                else:
                    # Not an API error or already using default model - re-raise
                    raise

            logger.debug(f"REQUEST_ID: {request_id} - Streaming selesai. Chunks: {chunk_count}")
            logger.debug(f"REQUEST_ID: {request_id} - Final message type: {type(final_message)}")

            if final_message is None or not getattr(final_message, "content", None):
                logger.warning(f"REQUEST_ID: {request_id} - Final message kosong, fallback.")
                final_message = AIMessage(content="Maaf, respons saya kosong. Silakan coba lagi.")

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
                "api_call_count": state.get("api_call_count", 0) + 1,
                "final_response": final_message.content,
                "model_used": model,  # Track which model was actually used
                "llm_fallback_error": state.get("llm_fallback_error")  # Propagate fallback error
            }
        except Exception as e:
            logger.error(
                f"REQUEST_ID: {request_id} - Gagal di agent_node: {e}",
                exc_info=True
            )
            span.set_status(trace.StatusCode.ERROR, f"Error: {e}")
            error_message = f"Maaf, terjadi kesalahan: {str(e)}"
            attempted_model = state.get("llm_model") or settings.DEFAULT_MODEL
            return {
                "chat_history": (
                    state.get("chat_history", []) +
                    [AIMessage(content=error_message)]
                ),
                "final_response": error_message,
                "errors": (
                    state.get("errors", []) +
                    [{"node": "agent_node", "error": str(e)}]
                ),
                "api_call_count": state.get("api_call_count", 0),
                "model_used": attempted_model
            }
