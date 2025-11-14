import json
import logging
from typing import Dict, Any, List, TYPE_CHECKING

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from tenacity import retry, stop_after_attempt, wait_exponential
from opentelemetry import trace
from fastapi import BackgroundTasks

from app.services.chat_engine.agent_state import AgentState
from app.services.chat_engine.llm_client import llm_flash_client
from app.services.chat_engine.agent_schemas import ToolApprovalRequest
from app.services.chat_engine.agent_prompts import REFLECTION_PROMPT

if TYPE_CHECKING:
    from app.services.chat_engine.tool_executor import ToolExecutor
    from app.services.chat_engine.tools.registry import ToolRegistry
    from app.services.calendar.schedule_service import ScheduleService

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# Lazy initialization - avoid circular import
_tool_executor = None

def _get_tool_executor():
    """Lazy load tool executor to avoid circular import."""
    global _tool_executor
    if _tool_executor is None:
        from app.services.chat_engine.tool_executor import ToolExecutor
        from app.services.chat_engine.tools.registry import TOOL_REGISTRY_INSTANCE
        _tool_executor = ToolExecutor(tool_registry=TOOL_REGISTRY_INSTANCE)
    return _tool_executor


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def reflection_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """Node #X: Memeriksa SEMUA tool calls untuk HiTL."""
    request_id = state.get("request_id")
    logger.info(f"REQUEST_ID: {request_id} - Node: reflection_node")
    
    last_message = state["chat_history"][-1]
    if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
        return {}

    with tracer.start_as_current_span("reflection_node") as span:
        approval_request = None
        
        for tool_call in last_message.tool_calls:
            tool_call_json = json.dumps(tool_call)
            
            try:
                prompt = REFLECTION_PROMPT.format(tool_call_json=tool_call_json)
                llm = llm_flash_client.with_structured_output(ToolApprovalRequest)
                result: ToolApprovalRequest = await llm.ainvoke([HumanMessage(content=prompt)], config=config)
                
                if result.approval_required:
                    logger.warning(f"REQUEST_ID: {request_id} - PERSETUJUAN DIPERLUKAN: {result.reason}")
                    approval_request = result.model_dump()
                    span.set_attribute("app.hitl_required", True)
                    break
            except Exception as e:
                logger.error(f"REQUEST_ID: {request_id} - Gagal di reflection_node: {e}", exc_info=True)
                approval_request = ToolApprovalRequest(
                    tool_name=tool_call.get("name", "unknown"),
                    tool_args=tool_call.get("args", {}),
                    reason=f"Gagal refleksi: {e}"
                ).model_dump()
                break

        if approval_request:
            return {
                "tool_approval_request": approval_request,
                "api_call_count": state.get("api_call_count", 0)  # Preserve
            }
        else:
            logger.info(f"REQUEST_ID: {request_id} - Semua tools aman.")
            return {"pending_tool_calls": last_message.tool_calls}


async def call_tools(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """Node #3: Mengeksekusi tools menggunakan DI dari config."""
    request_id = state.get("request_id")
    logger.info(f"REQUEST_ID: {request_id} - Node: call_tools")
    
    tool_calls_to_run = state.get("pending_tool_calls", [])
    if not tool_calls_to_run:
        return {}

    tool_messages: List[BaseMessage] = []
    
    try:
        dependencies = config["configurable"]["dependencies"]
        auth_info = dependencies["auth_info"]
        background_tasks: BackgroundTasks = dependencies["background_tasks"]
    except KeyError:
        logger.error(f"REQUEST_ID: {request_id} - Dependensi tidak ditemukan di config.")
        return {"errors": state.get("errors", []) + [{"node": "call_tools", "error": "Dependencies missing"}]}

    # Lazy import get_schedule_service to avoid circular import
    from app.core.dependencies import get_schedule_service
    
    schedule_service = get_schedule_service(auth_info)
    tool_executor = _get_tool_executor()
    
    for tool_call in tool_calls_to_run:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        
        if tool_name == "create_schedule_tool":
            tool_args["schedule_service"] = schedule_service
            tool_args["background_tasks"] = background_tasks
        elif tool_name == "create_canvas_block":
            tool_args["auth_info"] = auth_info
            
        with tracer.start_as_current_span(f"tool_call:{tool_name}") as span:
            result = await tool_executor.aexecute_tool(state, tool_call)
            span.set_attribute("app.tool.result", str(result)[:200])
            tool_messages.append(
                ToolMessage(content=str(result), tool_call_id=tool_call["id"])
            )
    
    updated_history = state.get("chat_history", []) + tool_messages

    return {
        "chat_history": updated_history,
        "api_call_count": state.get("api_call_count", 0)  # Preserve (tools don't count as LLM calls)
    }
