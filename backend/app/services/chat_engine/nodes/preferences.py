import logging
from typing import Dict, Any
from uuid import UUID

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from tenacity import retry, stop_after_attempt, wait_exponential
from opentelemetry import trace

from app.services.chat_engine.agent_state import AgentState
from app.services.chat_engine.llm_client import llm_flash_client
from app.services.chat_engine.agent_schemas import ExtractedPreference
from app.services.chat_engine.agent_prompts import EXTRACT_PREFERENCES_PROMPT
from app.services.chat_engine.user_preference_memory_service import save_preferences_to_db

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

def _count_tokens(text: str) -> int:
    """Estimasi token count."""
    if not text:
        return 0
    try:
        import tiktoken
        return len(tiktoken.get_encoding("cl100k_base").encode(text))
    except:
        return len(text) // 4


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def extract_preferences_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """Node #8: Berjalan di akhir, menggunakan DI dari config."""
    request_id = state.get("request_id")
    logger.info(f"REQUEST_ID: {request_id} - Node: extract_preferences_node")
    
    if not state.get("potential_preference"):
        logger.info(f"REQUEST_ID: {request_id} - Dilewati, tidak ada potensi preferensi.")
        return {}

    with tracer.start_as_current_span("extract_preferences_node") as span:
        try:
            dependencies = config["configurable"]["dependencies"]
            auth_info = dependencies["auth_info"]
            embedding_service = dependencies["embedding_service"]
            
            final_ai_response = state.get("final_response", "")
            
            prompt = EXTRACT_PREFERENCES_PROMPT.format(
                user_message=state.get("user_message", ""),
                ai_response=final_ai_response
            )
            input_tokens = _count_tokens(prompt)
            
            llm = llm_flash_client.with_structured_output(ExtractedPreference)
            result: ExtractedPreference = await llm.ainvoke([HumanMessage(content=prompt)], config=config)
            
            output_tokens = _count_tokens(result.model_dump_json())
            cost = state.get("cost_estimate", 0.0)

            span.set_attributes({
                "app.input_tokens": input_tokens,
                "app.output_tokens": output_tokens,
                "app.preferences_found": bool(result.preferences)
            })
            
            calls_llm = True
            
            if result.preferences:
                logger.info(f"REQUEST_ID: {request_id} - Menyimpan {len(result.preferences)} preferensi ke DB.")
                await save_preferences_to_db(
                    authed_client=auth_info["client"],
                    embedding_service=embedding_service,
                    user_id=UUID(state.get("user_id")),
                    preferences_list=[p.model_dump() for p in result.preferences]
                )
            else:
                calls_llm = False

            return {
                "extracted_preferences": result,
                "cost_estimate": cost,
                "output_token_count": state.get("output_token_count", 0) + output_tokens,
                "input_token_count": state.get("input_token_count", 0) + input_tokens,
                "api_call_count": state.get("api_call_count", 0) + (1 if calls_llm else 0)
            }
        except Exception as e:
            logger.error(f"REQUEST_ID: {request_id} - Gagal di extract_preferences_node: {e}", exc_info=True)
            span.set_status(trace.StatusCode.ERROR, f"Error: {e}")
            return {"errors": state.get("errors", []) + [{"node": "extract_preferences", "error": str(e)}]}
