import logging
from typing import Dict, Any

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from tenacity import retry, stop_after_attempt, wait_exponential
from opentelemetry import trace

from app.services.chat_engine.agent_state import AgentState
from app.services.chat_engine.llm_client import llm_flash_client
from app.services.chat_engine.agent_schemas import IntentClassification
from app.services.chat_engine.agent_prompts import CLASSIFY_INTENT_PROMPT

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
async def classify_intent(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """Node #1: Mengklasifikasikan niat pengguna."""
    request_id = state.get("request_id")
    logger.info(f"REQUEST_ID: {request_id} - Node: classify_intent")
    
    with tracer.start_as_current_span("classify_intent") as span:
        try:
            prompt = CLASSIFY_INTENT_PROMPT.format(
                chat_history=state.get("chat_history", []),
                user_message=state.get("user_message", "")
            )
            input_tokens = _count_tokens(prompt)
            
            # DEBUG: Log prompt yang dikirim
            logger.debug(f"REQUEST_ID: {request_id} - Prompt classify_intent (first 200 chars): {prompt[:200]}...")
            
            llm = llm_flash_client.with_structured_output(IntentClassification)
            result: IntentClassification = await llm.ainvoke([HumanMessage(content=prompt)], config=config)
            
            # DEBUG: Log response dari LLM
            logger.debug(f"REQUEST_ID: {request_id} - LLM result type: {type(result)}")
            if result:
                logger.debug(f"REQUEST_ID: {request_id} - LLM result: {result.model_dump()}")
            
            if not result:
                logger.error(f"REQUEST_ID: {request_id} - LLM mengembalikan None. Fallback ke simple_chat.")
                return {
                    "intent": "simple_chat",
                    "potential_preference": False,
                    "errors": state.get("errors", []) + [{"node": "classify_intent", "error": "LLM returned None"}]
                }
            
            # Validasi result adalah instance dari IntentClassification
            if not isinstance(result, IntentClassification):
                logger.error(f"REQUEST_ID: {request_id} - LLM tidak mengembalikan IntentClassification. Type: {type(result)}")
                return {
                    "intent": "simple_chat",
                    "potential_preference": False,
                    "errors": state.get("errors", []) + [{"node": "classify_intent", "error": f"Invalid type: {type(result)}"}]
                }
            
            output_tokens = _count_tokens(result.model_dump_json())
            cost = state.get("cost_estimate", 0.0)

            span.set_attributes({
                "app.intent": result.intent,
                "app.input_tokens": input_tokens,
                "app.output_tokens": output_tokens
            })
            
            logger.info(f"REQUEST_ID: {request_id} - Intent classified: {result.intent}")
            logger.debug(f"REQUEST_ID: {request_id} - Tokens - Input: {input_tokens}, Output: {output_tokens}")
            
            return {
                "intent": result.intent,
                "potential_preference": result.potential_preference,
                "cost_estimate": cost,
                "output_token_count": state.get("output_token_count", 0) + output_tokens,
                "input_token_count": state.get("input_token_count", 0) + input_tokens,
                "api_call_count": state.get("api_call_count", 0) + 1  # Increment
            }
        except Exception as e:
            logger.error(f"REQUEST_ID: {request_id} - Gagal di classify_intent: {e}", exc_info=True)
            span.set_status(trace.StatusCode.ERROR, f"Error: {e}")
            # Fallback ke simple_chat agar graph tetap lanjut
            return {
                "intent": "simple_chat",
                "potential_preference": False,
                "errors": state.get("errors", []) + [{"node": "classify_intent", "error": str(e)}]
            }
