import json
import asyncio
import logging
from typing import Dict, Any, TYPE_CHECKING
from uuid import UUID

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from tenacity import retry, stop_after_attempt, wait_exponential
from opentelemetry import trace

from app.services.chat_engine.agent_state import AgentState
from app.services.chat_engine.llm_client import llm_flash_client
from app.services.chat_engine.agent_schemas import RagQueryTransform, RerankedDocuments
from app.services.chat_engine.agent_prompts import (
    QUERY_TRANSFORM_PROMPT,
    RERANK_GEMINI_PROMPT,
    CONTEXT_COMPRESSION_PROMPT
)
from app.db.supabase_client import get_supabase_admin_async_client
from app.db.queries.conversation import context_queries

if TYPE_CHECKING:
    from app.services.embedding_service import GeminiEmbeddingService

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# Lazy initialization - avoid circular import
_rag_embedding_service = None

def _get_embedding_service():
    """Lazy load embedding service to avoid circular import."""
    global _rag_embedding_service
    if _rag_embedding_service is None:
        from app.services.embedding_service import GeminiEmbeddingService
        _rag_embedding_service = GeminiEmbeddingService()
    return _rag_embedding_service

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
async def query_transform(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """Node #3: Transform ambiguous query menjadi search query yang jelas."""
    request_id = state.get("request_id", "unknown")
    logger.info(f"REQUEST_ID: {request_id} - Node: query_transform")
    
    try:
        prompt = QUERY_TRANSFORM_PROMPT.format(
            chat_history=state.get("chat_history", []),
            user_message=state.get("user_message", "")
        )
        input_tokens = _count_tokens(prompt)
        
        llm = llm_flash_client.with_structured_output(RagQueryTransform)
        result: RagQueryTransform = await llm.ainvoke([HumanMessage(content=prompt)], config=config)
        
        output_tokens = _count_tokens(result.model_dump_json())
        cost = state.get("cost_estimate", 0.0)

        logger.info(f"REQUEST_ID: {request_id} - Query transformed")
        logger.debug(f"REQUEST_ID: {request_id} - RAG query: {result.rag_query[:100]}...")
        
        return {
            "transformed_query": result.rag_query,
            "cost_estimate": cost,
            "output_token_count": state.get("output_token_count", 0) + output_tokens,
            "input_token_count": state.get("input_token_count", 0) + input_tokens,
            "api_call_count": state.get("api_call_count", 0) + 1  # Increment
        }
    except Exception as e:
        logger.error(f"REQUEST_ID: {request_id} - Gagal di query_transform: {e}", exc_info=True)
        # REMOVE: span.set_status(trace.StatusCode.ERROR, f"Error: {e}")
        # Return fallback instead of raising to prevent retry loop
        return {
            "transformed_query": state.get("user_message", ""),
            "cost_estimate": state.get("cost_estimate", 0.0),
            "output_token_count": state.get("output_token_count", 0),
            "input_token_count": state.get("input_token_count", 0),
            "api_call_count": state.get("api_call_count", 0)
        }


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def retrieve_context(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """Node #4: Retrieve relevant context from vector store (RAG)."""
    request_id = state.get("request_id", "unknown")
    logger.info(f"REQUEST_ID: {request_id} - Node: retrieve_context")
    
    try:
        prompt = QUERY_TRANSFORM_PROMPT.format(
            chat_history=state.get("chat_history", []),
            user_message=state.get("user_message", "")
        )
        input_tokens = _count_tokens(prompt)
        
        llm = llm_flash_client.with_structured_output(RagQueryTransform)
        result: RagQueryTransform = await llm.ainvoke([HumanMessage(content=prompt)], config=config)
        
        output_tokens = _count_tokens(result.model_dump_json())
        cost = state.get("cost_estimate", 0.0)

        logger.info(f"REQUEST_ID: {request_id} - Query transformed")
        
        return {
            "transformed_query": result.rag_query,
            "cost_estimate": cost,
            "output_token_count": state.get("output_token_count", 0) + output_tokens,
            "input_token_count": state.get("input_token_count", 0) + input_tokens,
            "api_call_count": state.get("api_call_count", 0) + 1  # Increment
        }
    except Exception as e:
        logger.error(f"REQUEST_ID: {request_id} - Gagal di query_transform: {e}", exc_info=True)
        ts_query_fallback = " & ".join(state.get("user_message", "").split()[:5])
        return {"rag_query": state.get("user_message"), "ts_query": ts_query_fallback}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def retrieve_context(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """Node #4: Retrieve relevant context from vector store (RAG)."""
    request_id = state.get("request_id", "unknown")
    logger.info(f"REQUEST_ID: {request_id} - Node: retrieve_context")
    
    try:
        prompt = QUERY_TRANSFORM_PROMPT.format(
            chat_history=state.get("chat_history", []),
            user_message=state.get("user_message", "")
        )
        input_tokens = _count_tokens(prompt)
        
        llm = llm_flash_client.with_structured_output(RagQueryTransform)
        result: RagQueryTransform = await llm.ainvoke([HumanMessage(content=prompt)], config=config)
        
        output_tokens = _count_tokens(result.model_dump_json())
        cost = state.get("cost_estimate", 0.0)

        logger.info(f"REQUEST_ID: {request_id} - Query transformed")
        
        return {
            "transformed_query": result.rag_query,
            "cost_estimate": cost,
            "output_token_count": state.get("output_token_count", 0) + output_tokens,
            "input_token_count": state.get("input_token_count", 0) + input_tokens,
            "api_call_count": state.get("api_call_count", 0) + 1  # Increment
        }
    except Exception as e:
        logger.error(f"REQUEST_ID: {request_id} - Gagal di query_transform: {e}", exc_info=True)
        ts_query_fallback = " & ".join(state.get("user_message", "").split()[:5])
        return {"rag_query": state.get("user_message"), "ts_query": ts_query_fallback}


async def rerank_context(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """Node #6: Menggunakan LLM Flash sebagai Reranker."""
    request_id = state.get("request_id")
    logger.info(f"REQUEST_ID: {request_id} - Node: rerank_context")
    
    rag_query = state.get("rag_query")
    retrieved_docs = state.get("retrieved_docs", [])
    
    if not retrieved_docs:
        return {"reranked_docs": []}

    with tracer.start_as_current_span("rerank_context_gemini") as span:
        try:
            docs_with_index = []
            for i, doc in enumerate(retrieved_docs):
                content = doc.get("content", doc.get("summary_text", ""))
                docs_with_index.append({
                    "index": i,
                    "content": content,
                    "source_id": doc.get("source_id", "unknown")
                })
            
            prompt = RERANK_GEMINI_PROMPT.format(
                rag_query=rag_query,
                retrieved_docs_json=json.dumps(docs_with_index, indent=2)
            )
            input_tokens = _count_tokens(prompt)
            
            llm = llm_flash_client.with_structured_output(RerankedDocuments)
            result: RerankedDocuments = await llm.ainvoke([HumanMessage(content=prompt)], config=config)
            
            output_tokens = _count_tokens(result.model_dump_json())
            cost = state.get("cost_estimate", 0.0)

            final_docs = []
            for res in result.reranked_results:
                original_doc = retrieved_docs[res.original_index]
                original_doc["rank"] = res.relevance_score
                final_docs.append(original_doc)
                
            span.set_attributes({
                "app.rerank.docs_in": len(retrieved_docs),
                "app.rerank.docs_out": len(final_docs),
                "app.input_tokens": input_tokens,
                "app.output_tokens": output_tokens
            })
            
            return {
                "retrieved_contexts": final_docs,
                "cost_estimate": cost,
                "api_call_count": state.get("api_call_count", 0)  # Preserve (no LLM)
            }
            
        except Exception as e:
            logger.error(f"REQUEST_ID: {request_id} - Gagal di rerank_context: {e}", exc_info=True)
            span.set_status(trace.StatusCode.ERROR, f"Error: {e}")
            return {"reranked_docs": retrieved_docs[:5]}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def context_compression(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """Node #7: Compress & summarize retrieved contexts."""
    request_id = state.get("request_id")
    logger.info(f"REQUEST_ID: {request_id} - Node: context_compression")
    
    with tracer.start_as_current_span("context_compression") as span:
        try:
            reranked_docs = state.get("reranked_docs", [])
            if not reranked_docs:
                return {"compressed_context": "(Tidak ada konteks RAG yang relevan ditemukan.)"}

            doc_texts = [f"Sumber: {doc['source_id']}\nKonten: {doc['content']}\n---" for doc in reranked_docs]

            prompt = CONTEXT_COMPRESSION_PROMPT.format(
                rag_query=state.get("rag_query"),
                reranked_docs="\n".join(doc_texts)
            )
            input_tokens = _count_tokens(prompt)
            
            result = await llm_flash_client.ainvoke([HumanMessage(content=prompt)], config=config)
            compressed_context = result.content if result.content else ""
            
            output_tokens = _count_tokens(compressed_context)
            cost = state.get("cost_estimate", 0.0)

            span.set_attributes({"app.input_tokens": input_tokens, "app.output_tokens": output_tokens})
            
            logger.info(f"REQUEST_ID: {request_id} - Context compressed successfully")
            logger.debug(f"REQUEST_ID: {request_id} - Compressed length: {len(result.content)} chars")
            
            return {
                "compressed_context": result.content,
                "cost_estimate": cost,
                "output_token_count": state.get("output_token_count", 0) + output_tokens,
                "input_token_count": state.get("input_token_count", 0) + input_tokens,
                "api_call_count": state.get("api_call_count", 0) + 1  # Increment
            }
            
        except Exception as e:
            logger.error(f"REQUEST_ID: {request_id} - Gagal di context_compression: {e}", exc_info=True)
            span.set_status(trace.StatusCode.ERROR, f"Error: {e}")
        except Exception as e:
            logger.error(f"REQUEST_ID: {request_id} - Gagal di context_compression: {e}", exc_info=True)
            span.set_status(trace.StatusCode.ERROR, f"Error: {e}")
            return {"compressed_context": "(Gagal memproses konteks RAG.)"}
