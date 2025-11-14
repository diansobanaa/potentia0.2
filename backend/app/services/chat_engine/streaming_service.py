"""
SSE streaming service for LangGraph agent events.
"""
import json
import logging
from typing import AsyncGenerator, List, Optional
from uuid import UUID
from datetime import datetime
import time

from langchain_core.messages import BaseMessage, AIMessageChunk, ToolMessage
from langchain_core.runnables import RunnableConfig

from app.services.chat_engine.agent_state import AgentState
from app.services.chat_engine.streaming_schemas import StreamError
from app.services.chat_engine.helpers import TokenCounter
from app.services.chat_engine.helpers.observability_collector import ObservabilityCollector
from app.core.config import settings

logger = logging.getLogger(__name__)


class StreamingService:
    """Service for handling LangGraph agent event streaming."""
    
    @staticmethod
    async def stream_agent_response(
        langgraph_agent,
        request_id: str,
        user_id: str,
        conversation_id: str,
        user_message: str,
        chat_history: List[BaseMessage],
        permissions: List[str],
        auth_info,
        embedding_service,
        background_tasks,
        llm_config: Optional[dict] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream LangGraph agent events as Server-Sent Events (SSE).
        
        Args:
            langgraph_agent: Compiled LangGraph agent
            request_id: Unique request ID for tracking
            user_id: User UUID (as string)
            conversation_id: Conversation UUID (as string)
            user_message: User's input message
            chat_history: Previous chat messages
            permissions: User's permission scopes
            auth_info: Authentication info dict
            embedding_service: Embedding service instance
            background_tasks: FastAPI BackgroundTasks
            llm_config: Optional LLM configuration overrides
            
        Yields:
            str: JSON-formatted SSE events
        """
        final_ai_response_chunks = []
        current_node = None
        final_state = None

        # Local counters (fallback if AgentState doesn't accumulate)
        total_input_tokens_stream = 0
        total_output_tokens_stream = 0
        model_used_stream = None

        # NEW: Debug counters
        event_count = 0

        # NEW: Start observability tracking
        ObservabilityCollector.start_request(request_id, conversation_id, user_message)
        
        # Track current LLM call
        current_llm_call = {
            "node": None,
            "start_time": None,
            "messages": [],
            "input_tokens": 0
        }

        try:
            # Send metadata first (user needs this)
            yield json.dumps({
                "type": "metadata",
                "payload": {
                    "conversation_id": conversation_id,
                    "request_id": request_id
                }
            }) + "\n"
            
            # Track if we've sent errorStatus
            error_status_sent = False

            # Build initial agent state
            initial_state = AgentState(
                request_id=request_id,
                trace_id=None,
                user_id=user_id,
                permissions=permissions,
                conversation_id=conversation_id,
                created_at=datetime.utcnow(),
                user_message=user_message,
                chat_history=chat_history,
                cost_estimate=0.0,
                input_token_count=0,
                output_token_count=0,
                api_call_count=0  # Initialize to 0
            )

            # Extract LLM config (frontend-driven)
            if llm_config:
                model = llm_config.get("model")
                temperature = llm_config.get(
                    "temperature",
                    settings.DEFAULT_TEMPERATURE
                )
                max_tokens = llm_config.get("max_tokens")
                logger.info(
                    f"✅ StreamingService extracted llm_config: "
                    f"model={model}, temp={temperature}, "
                    f"max_tokens={max_tokens}"
                )
            else:
                model = settings.DEFAULT_MODEL
                temperature = settings.DEFAULT_TEMPERATURE
                max_tokens = None
                logger.warning(
                    f"⚠️  StreamingService: No llm_config provided, "
                    f"using defaults: model={model}, temp={temperature}"
                )

            logger.info(
                f"🔧 Creating RunnableConfig with model={model}, "
                f"temp={temperature}"
            )

            # Update initial_state with model info (CRITICAL: Pass via state!)
            initial_state["model_used"] = model
            initial_state["llm_model"] = model
            initial_state["llm_temperature"] = temperature
            initial_state["llm_max_tokens"] = max_tokens

            config = RunnableConfig(
                configurable={
                    "thread_id": conversation_id,
                    "dependencies": {
                        "auth_info": auth_info,
                        "embedding_service": embedding_service,
                        "background_tasks": background_tasks
                    },
                    "llm": {
                        "model": model,
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    },
                }
            )
            
            # Verify config structure (safe access)
            logger.debug(
                f"🔍 Created RunnableConfig, type: {type(config)}"
            )
            if isinstance(config, dict):
                logger.debug(
                    f"🔍 Config is dict with keys: "
                    f"{list(config.get('configurable', {}).keys())}"
                )
            elif hasattr(config, 'configurable'):
                logger.debug(
                    f"🔍 Config.configurable keys: "
                    f"{list(config.configurable.keys())}"
                )
            
            logger.info(f"🤖 Model: {model} (temp={temperature})")

            # Helper: robustly extract messages contents from event data
            def _extract_messages_contents(data: dict) -> List[str]:
                # Try common locations
                candidates = []
                # direct fields
                msg = data.get("messages")
                if msg: candidates.append(msg)
                inp = data.get("input")
                if inp: candidates.append(inp)
                # kwargs fields
                kwargs = data.get("kwargs") or {}
                kw_msgs = kwargs.get("messages")
                if kw_msgs: candidates.append(kw_msgs)
                kw_inp = kwargs.get("input") or kwargs.get("inputs")
                if kw_inp: candidates.append(kw_inp)

                contents: List[str] = []

                def _flatten(xs):
                    for x in xs:
                        if isinstance(x, (list, tuple)):
                            yield from _flatten(x)
                        else:
                            yield x

                for cand in candidates:
                    try:
                        for item in _flatten(cand if isinstance(cand, list) else [cand]):
                            # LangChain message object
                            content = getattr(item, "content", None)
                            if content is None and isinstance(item, dict):
                                content = item.get("content")
                            if isinstance(content, str) and content:
                                contents.append(content)
                    except Exception:
                        continue
                return contents

            async for event in langgraph_agent.astream_events(initial_state, config=config, version="v1"):
                kind = event["event"]
                
                # LOG PROMPT TO TERMINAL (NOT sent to user)
                if kind == "on_chat_model_start":
                    data = event.get("data", {}) or {}
                    node_name = event.get("name", "unknown")
                    
                    # Extract prompt messages
                    messages = data.get("input", {}).get("messages", [])
                    
                    # Flatten nested lists
                    def flatten_messages(msgs):
                        for item in msgs:
                            if isinstance(item, list):
                                yield from flatten_messages(item)
                            else:
                                yield item
                    
                    # LOG to terminal only
                    logger.info(f"🔍 PROMPT_LOG [node={node_name}] - Sending prompt to LLM")
                    total_tokens = 0
                    for idx, msg in enumerate(flatten_messages(messages)):
                        # Handle both LangChain message objects and dicts
                        if hasattr(msg, "type"):
                            role = msg.type
                            content = getattr(msg, "content", "")
                        elif isinstance(msg, dict):
                            role = msg.get("type", "unknown")
                            content = msg.get("content", "")
                        else:
                            continue
                        
                        tokens = TokenCounter.count_tokens(content) if content else 0
                        total_tokens += tokens
                        
                        # LOG each message to terminal
                        logger.info(f"  [{idx}] {role} ({tokens} tokens): {content}...")
                    
                    logger.info(f"  Total tokens: {total_tokens}")
                    
                    # Accumulate for final_state
                    total_input_tokens_stream += total_tokens
                
                # Send status updates to user (clean, no internal details)
                if kind == "on_chain_start":
                    node_name = event["name"]
                    current_node = node_name
                    
                    # Check for fallback error and send errorStatus before first status
                    if not error_status_sent and node_name == "agent_node":
                        # Check if there's a fallback error in initial_state
                        fallback_err = initial_state.get("llm_fallback_error")
                        if fallback_err:
                            error_str = fallback_err.get("error", "")
                            original_model = fallback_err.get("original_model", "")
                            
                            # Determine error message
                            if "429" in error_str or "quota" in error_str.lower():
                                if "suspended" in error_str.lower():
                                    msg = f"⚠️ Model '{original_model}' suspended. Akun billing habis. Menggunakan fallback model."
                                else:
                                    msg = f"⚠️ Model '{original_model}' rate limit/quota habis. Menggunakan fallback model."
                            elif "401" in error_str or "unauthorized" in error_str.lower():
                                msg = f"⚠️ Model '{original_model}' autentikasi gagal. Menggunakan fallback model."
                            else:
                                msg = f"⚠️ Model '{original_model}' error: {error_str[:100]}. Menggunakan fallback model."
                            
                            yield json.dumps({"type": "errorStatus", "payload": msg}) + "\n"
                            error_status_sent = True
                            logger.info(f"REQUEST_ID: {request_id} - Sent errorStatus to user")
                    
                    status_messages = {
                        "classify_intent": "Menganalisis niat...",
                        "query_transform": "Memperjelas kueri...",
                        "retrieve_context": "Mencari ingatan...",
                        "rerank_context": "Memfilter ingatan...",
                        "context_compression": "Meringkas ingatan...",
                        "agent_node": "Merumuskan jawaban..."
                    }
                    if node_name in status_messages:
                        yield json.dumps({"type": "status", "payload": status_messages[node_name]}) + "\n"
                
                # Stream token chunks to user
                elif kind == "on_chat_model_stream":
                    if current_node == "agent_node":
                        chunk = event["data"]["chunk"]
                        if isinstance(chunk, AIMessageChunk) and chunk.content:
                            token = chunk.content
                            
                            # Stream all content as token_chunk (including thinkingDiv)
                            final_ai_response_chunks.append(token)
                            try:
                                total_output_tokens_stream += TokenCounter.count_tokens(token)
                            except Exception:
                                pass
                            yield json.dumps({"type": "token_chunk", "payload": token}) + "\n"
                
                # Handle chain end
                elif kind == "on_chain_end":
                    current_node = None
                    node_name = event["name"]
                    output_data = event["data"]["output"]
                    
                    # DEBUG: Log api_call_count after each node
                    if output_data and isinstance(output_data, dict):
                        api_count = output_data.get("api_call_count", "N/A")
                        logger.debug(f"🔍 After node '{node_name}': api_call_count={api_count}")
                    
                    # Handle tool approval request (HiTL)
                    if node_name == "reflection_node":
                        if output_data.get("tool_approval_request"):
                            logger.warning(f"REQUEST_ID: {request_id} - Graph paused for approval")
                            yield json.dumps({
                                "type": "tool_approval_required",
                                "payload": output_data["tool_approval_request"]
                            }) + "\n"
                    
                    # Handle tool execution result
                    elif node_name == "call_tools":
                        last_tool_msg: ToolMessage = output_data["chat_history"][-1]
                        yield json.dumps({
                            "type": "status",
                            "payload": f"Hasil: {str(last_tool_msg.content)[:50]}..."
                        }) + "\n"
                    
                    # Capture final state from graph
                    if output_data and isinstance(output_data, dict):
                        final_state = output_data
                        
                        # Check for fallback error in final state (in case not caught earlier)
                        if not error_status_sent and node_name == "agent_node":
                            fallback_err = output_data.get("llm_fallback_error")
                            if fallback_err:
                                error_str = fallback_err.get("error", "")
                                original_model = fallback_err.get("original_model", "")
                                
                                if "429" in error_str or "quota" in error_str.lower():
                                    if "suspended" in error_str.lower():
                                        msg = f"⚠️ Model '{original_model}' suspended. Akun billing habis. Menggunakan fallback model."
                                    else:
                                        msg = f"⚠️ Model '{original_model}' rate limit/quota habis. Menggunakan fallback model."
                                elif "401" in error_str or "unauthorized" in error_str.lower():
                                    msg = f"⚠️ Model '{original_model}' autentikasi gagal. Menggunakan fallback model."
                                else:
                                    msg = f"⚠️ Model '{original_model}' error. Menggunakan fallback model."
                                
                                yield json.dumps({"type": "errorStatus", "payload": msg}) + "\n"
                                error_status_sent = True
                                logger.info(f"REQUEST_ID: {request_id} - Sent errorStatus to user (on_chain_end)")
            
            # No need to send final_response separately since fallback will stream normally
            
            # Calculate metrics
            input_total = (
                (final_state or {}).get("input_token_count") or
                total_input_tokens_stream
            )
            output_total = (
                (final_state or {}).get("output_token_count") or
                total_output_tokens_stream
            )
            api_calls = (final_state or {}).get("api_call_count", 0)
            # Use model_used from state (includes attempted model on error)
            model_used = (
                (final_state or {}).get("model_used") or
                model_used_stream or
                settings.DEFAULT_MODEL
            )
            
            # Calculate cost
            pricing = {
                "input": 0.000035 / 1000,
                "output": 0.00014 / 1000
            }
            cost = (input_total * pricing["input"]) + (output_total * pricing["output"])
            
            # LOG SUMMARY to terminal
            logger.info(f"📊 TOKEN SUMMARY [request_id={request_id}]")
            logger.info(f"  Input tokens:  {input_total}")
            logger.info(f"  Output tokens: {output_total}")
            logger.info(f"  API calls:     {api_calls}")  # NEW
            logger.info(f"  Total cost:    ${cost:.6f}")
            logger.info(f"  Model:         {model_used}")
            
            # Send clean final_state to user
            yield json.dumps({
                "type": "final_state",
                "payload": {
                    "input_token_count": int(input_total),
                    "output_token_count": int(output_total),
                    "api_call_count": int(api_calls),  # NEW
                    "cost_estimate": round(cost, 6),
                    "model_used": model_used
                }
            }) + "\n"
            
            logger.info(f"REQUEST_ID: {request_id} - Stream finished")
            
        except Exception as e:
            logger.error(f"Stream error (req_id: {request_id}): {e}", exc_info=True)
            error_payload = StreamError(detail=f"Stream error: {e}", status_code=500)
            yield error_payload.model_dump_json() + "\n"
