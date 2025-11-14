import json
import logging
from typing import Dict, Any, List, TYPE_CHECKING
from uuid import UUID

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from opentelemetry import trace

from app.services.chat_engine.agent_state import AgentState
from app.services.chat_engine.llm_client import llm_flash_client
from app.services.chat_engine.agent_schemas import PruningResult
from app.services.chat_engine.agent_prompts import (
    CONTEXT_PRUNING_PROMPT,
    CONTEXT_SUMMARIZATION_PROMPT
)

if TYPE_CHECKING:
    from app.db.queries.conversation import context_queries, message_queries

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# Konstanta
CONTEXT_WINDOW_TOKEN_LIMIT = 8000
RECENT_MESSAGES_TO_KEEP = 10

# Helper functions untuk token counting
def _count_tokens(text: str) -> int:
    """Estimasi jumlah token dalam teks."""
    if not text:
        return 0
    try:
        import tiktoken
        tokenizer = tiktoken.get_encoding("cl100k_base")
        return len(tokenizer.encode(text))
    except:
        return len(text) // 4

def _count_message_tokens(messages: List[BaseMessage]) -> int:
    """Hitung total token dalam list messages."""
    count = 0
    for msg in messages:
        if msg.content:
            count += _count_tokens(msg.content)
    return count


async def load_full_history(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """Node #A: Memuat SEMUA riwayat dari DB."""
    request_id = state.get("request_id")
    logger.info(f"REQUEST_ID: {request_id} - Node: load_full_history")
    
    # Import here to avoid circular dependency at module level
    from app.db.queries.conversation import message_queries
    
    dependencies = config["configurable"]["dependencies"]
    auth_info = dependencies["auth_info"]
    client = auth_info["client"]
    user_id = UUID(state.get("user_id"))
    conversation_id = UUID(state.get("conversation_id"))

    try:
        messages_data = await message_queries.get_all_conversation_messages(
            client, user_id, conversation_id, limit=1000
        )
        
        history: List[BaseMessage] = []
        for msg in messages_data:
            if msg['role'] == 'user':
                history.append(HumanMessage(content=msg.get("content", "")))
            elif msg['role'] == 'assistant':
                history.append(AIMessage(content=msg.get("content", "")))
        
        history.append(HumanMessage(content=state.get("user_message")))
        
        return {
            "chat_history": history,
            "api_call_count": state.get("api_call_count", 0)  # Preserve
        }
    except Exception as e:
        logger.error(f"REQUEST_ID: {request_id} - Gagal memuat riwayat penuh: {e}")
        return {"errors": state.get("errors", []) + [{"node": "load_full_history", "error": str(e)}]}


async def manage_context_window(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """Node #B: Implementasi logika Pruning P1-P4."""
    request_id = state.get("request_id")
    logger.info(f"REQUEST_ID: {request_id} - Node: manage_context_window")
    
    full_history = state.get("chat_history", [])
    total_tokens = _count_message_tokens(full_history)
    
    if total_tokens <= CONTEXT_WINDOW_TOKEN_LIMIT:
        logger.info(f"REQUEST_ID: {request_id} - Konteks muat ({total_tokens} tokens).")
        return {"total_tokens": total_tokens}

    logger.warning(f"REQUEST_ID: {request_id} - Konteks terlalu panjang ({total_tokens} tokens). Memulai pruning...")
    
    messages_to_keep_recent = full_history[-RECENT_MESSAGES_TO_KEEP:]
    messages_to_evaluate = full_history[:-RECENT_MESSAGES_TO_KEEP]

    eval_json = [{"index": i, "role": msg.type, "content": msg.content} for i, msg in enumerate(messages_to_evaluate)]
    
    try:
        prompt = CONTEXT_PRUNING_PROMPT.format(messages_json=json.dumps(eval_json, indent=2))
        llm = llm_flash_client.with_structured_output(PruningResult)
        result: PruningResult = await llm.ainvoke([HumanMessage(content=prompt)], config=config)
        
        pruned_history: List[BaseMessage] = []
        messages_to_summarize: List[BaseMessage] = []
        
        priority_map = {p.index: p.priority for p in result.prioritized_messages}
        
        for i, msg in enumerate(messages_to_evaluate):
            priority = priority_map.get(i)
            if priority == "P1":
                pruned_history.append(msg)
            elif priority == "P2":
                messages_to_summarize.append(msg)

        final_pruned_history = pruned_history + messages_to_keep_recent
        final_tokens = _count_message_tokens(final_pruned_history)

        logger.info(f"REQUEST_ID: {request_id} - Pruning selesai. {len(pruned_history)} (P1) + {len(messages_to_keep_recent)} (P4).")

        return {
            "chat_history": final_pruned_history,
            "messages_to_summarize": messages_to_summarize,
            "total_tokens": final_tokens,
            "api_call_count": state.get("api_call_count", 0)  # Preserve
        }

    except Exception as e:
        logger.error(f"REQUEST_ID: {request_id} - Gagal di pruning: {e}. Fallback.")
        final_pruned_history = full_history[-RECENT_MESSAGES_TO_KEEP:]
        return {
            "chat_history": final_pruned_history,
            "total_tokens": _count_message_tokens(final_pruned_history),
            "api_call_count": state.get("api_call_count", 0)  # Preserve
        }


async def summarize_context(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """Node #C: Meringkas pesan P2 dan menyimpannya ke DB."""
    request_id = state.get("request_id")
    messages_to_summarize = state.get("messages_to_summarize", [])
    
    if not messages_to_summarize:
        logger.info(f"REQUEST_ID: {request_id} - Node: summarize_context (Dilewati)")
        return {}

    logger.info(f"REQUEST_ID: {request_id} - Node: summarize_context ({len(messages_to_summarize)} pesan P2)")
    
    # Import here to avoid circular dependency
    from app.db.queries.conversation import context_queries
    
    dependencies = config["configurable"]["dependencies"]
    auth_info = dependencies["auth_info"]
    client = auth_info["client"]
    user_id = UUID(state.get("user_id"))
    conversation_id = UUID(state.get("conversation_id"))
    
    try:
        transcript = "\n".join([f"{msg.type}: {msg.content}" for msg in messages_to_summarize])
        prompt = CONTEXT_SUMMARIZATION_PROMPT.format(messages_to_summarize=transcript)
        
        llm = llm_flash_client
        result = await llm.ainvoke([HumanMessage(content=prompt)], config=config)
        summary_text = result.content
        
        if summary_text:
            logger.info(f"REQUEST_ID: {request_id} - Menyimpan ringkasan P2 ke summary_memory.")
            await context_queries.create_summary_for_conversation(
                client, user_id, conversation_id, summary_text
            )
        
        return {
            "chat_history": messages_to_summarize,  # Assuming we return the summarized messages
            "api_call_count": state.get("api_call_count", 0) + 1  # Increment if LLM called
        }
    except Exception as e:
        logger.error(f"REQUEST_ID: {request_id} - Gagal di summarize_context: {e}")
        return {"errors": state.get("errors", []) + [{"node": "summarize_context", "error": str(e)}]}


async def check_context_length(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """Node #9: Memeriksa total token."""
    request_id = state.get("request_id")
    logger.info(f"REQUEST_ID: {request_id} - Node: check_context_length")
    
    total_tokens = state.get("total_tokens", 0)
    overflow = total_tokens > CONTEXT_WINDOW_TOKEN_LIMIT
    
    return {
        "context_overflow": overflow,
        "api_call_count": state.get("api_call_count", 0)  # Preserve
    }


async def prune_and_summarize_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """Node #10: Fallback pruning di akhir flow."""
    request_id = state.get("request_id")
    logger.warning(f"REQUEST_ID: {request_id} - Node: prune_and_summarize_node")
    
    dependencies = config["configurable"]["dependencies"]
    auth_info = dependencies["auth_info"]
    client = auth_info["client"]
    user_id = UUID(state.get("user_id"))
    
    full_history = state.get("chat_history", [])
    messages_to_keep_recent = full_history[-RECENT_MESSAGES_TO_KEEP:]
    messages_to_evaluate = full_history[:-RECENT_MESSAGES_TO_KEEP]

    eval_json = [{"index": i, "role": msg.type, "content": msg.content} for i, msg in enumerate(messages_to_evaluate)]
    
    with tracer.start_as_current_span("prune_and_summarize") as span:
        try:
            pruning_prompt = CONTEXT_PRUNING_PROMPT.format(messages_json=json.dumps(eval_json, indent=2))
            pruning_llm = llm_flash_client.with_structured_output(PruningResult)
            pruning_result: PruningResult = await pruning_llm.ainvoke([HumanMessage(content=pruning_prompt)], config=config)
            
            messages_to_summarize: List[BaseMessage] = []
            priority_map = {p.index: p.priority for p in pruning_result.prioritized_messages}
            
            for i, msg in enumerate(messages_to_evaluate):
                if priority_map.get(i) == "P2":
                    messages_to_summarize.append(msg)
            
            if messages_to_summarize:
                transcript = "\n".join([f"{msg.type}: {msg.content}" for msg in messages_to_summarize])
                summary_prompt = CONTEXT_SUMMARIZATION_PROMPT.format(messages_to_summarize=transcript)
                
                summary_llm = llm_flash_client
                summary_result = await summary_llm.ainvoke([HumanMessage(content=summary_prompt)], config=config)
                summary_text = summary_result.content
                
                if summary_text:
                    logger.info(f"REQUEST_ID: {request_id} - Menyimpan ringkasan P2.")
                    span.set_attribute("app.summary_created", True)
            
            return {
                "chat_history": messages_to_keep_recent,  # Assuming we return the recent messages
                "api_call_count": state.get("api_call_count", 0)  # Preserve or +1 if LLM called
            }
        
        except Exception as e:
            logger.error(f"REQUEST_ID: {request_id} - Gagal di prune_and_summarize_node: {e}")
            span.set_status(trace.StatusCode.ERROR, f"Error: {e}")
            return {"errors": state.get("errors", []) + [{"node": "prune_and_summarize", "error": str(e)}]}
