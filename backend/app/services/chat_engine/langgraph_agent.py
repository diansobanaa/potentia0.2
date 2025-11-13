# File: backend/app/services/chat_engine/langgraph_agent.py
# (Final v3.2 - Perbaikan Impor 'interruptException' & 'RedisSaver')
import logging
import json
import tiktoken
import re 
import asyncio
from typing import Dict, Any, List, Optional
from uuid import UUID
from tenacity import retry, stop_after_attempt, wait_exponential
from opentelemetry import trace
from langchain_core.load import dumps, loads
from langgraph.checkpoint.redis import RedisSaver as OldRedisSaver
from langgraph.checkpoint.base import CheckpointTuple

# === [PERBAIKAN v3.2] ===
from langgraph.graph import StateGraph, END
from langgraph.types import interrupt
# === AKHIR PERBAIKAN ===


from langchain_core.messages import (
    HumanMessage, SystemMessage, BaseMessage, AIMessage, ToolMessage, AIMessageChunk
)
from langchain_core.runnables import RunnableConfig
from pydantic import ValidationError

from app.core.config import settings
from app.services.redis_rate_limiter import rate_limiter
from app.services.chat_engine.agent_state import AgentState
from app.services.chat_engine.llm_client import llm_flash_client, llm_pro_client
from app.services.chat_engine.agent_schemas import (
    IntentClassification, RagQueryTransform, ToolApprovalRequest, ExtractedPreference,
    RerankedDocuments,
    PruningResult 
)
from app.services.chat_engine.agent_prompts import (
    CLASSIFY_INTENT_PROMPT, AGENT_SYSTEM_PROMPT, 
    QUERY_TRANSFORM_PROMPT, CONTEXT_COMPRESSION_PROMPT,
    REFLECTION_PROMPT, EXTRACT_PREFERENCES_PROMPT,
    RERANK_GEMINI_PROMPT,
    CONTEXT_PRUNING_PROMPT, CONTEXT_SUMMARIZATION_PROMPT
)

from app.services.chat_engine.tool_executor import ToolExecutor
from app.services.chat_engine.tools.registry import TOOL_REGISTRY_INSTANCE
# (Impor Reranker Cohere tidak ada, sudah benar)

# Impor dependensi
from app.services.calendar.schedule_service import ScheduleService
from fastapi import BackgroundTasks
from app.services.embedding_service import GeminiEmbeddingService
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.dependencies import AuthInfoDep, EmbeddingServiceDep, get_schedule_service

from app.db.supabase_client import get_supabase_admin_async_client
from app.db.queries.conversation import context_queries, message_queries
from app.services.chat_engine.user_preference_memory_service import save_preferences_to_db

# === [PERBAIKAN FINAL] Serializer kustom kompatibel LangGraph terbaru ===
class LangChainSerializer:
    """
    Menserialisasi obyek LangChain (mis. HumanMessage, AIMessage)
    agar kompatibel dengan mekanisme checkpoint Redis di LangGraph.
    """

    def dumps(self, obj: Any) -> bytes:
        """Serialize obyek Python menjadi bytes JSON."""
        from langchain_core.load.dump import dumps as lc_dumps
        import json

        try:
            # lc_dumps tahu cara menangani HumanMessage
            return lc_dumps(obj).encode("utf-8")
        except Exception:
            # Fallback untuk tipe data sederhana
            return json.dumps(obj, default=str).encode("utf-8")

    def loads(self, data: bytes) -> Any:
        """Deserialize bytes JSON menjadi obyek Python."""
        from langchain_core.load.load import loads as lc_loads
        import json

        s = data.decode("utf-8")
        try:
            # lc_loads tahu cara mengembalikan string menjadi HumanMessage
            return lc_loads(s)
        except Exception:
            return json.loads(s)

    # === Tambahan agar kompatibel dengan LangGraph >=0.1.x ===
    def dumps_typed(self, obj: Any) -> tuple[str, bytes]:
        """Dikonsumsi oleh LangGraph RedisSaver."""
        type_name = obj.__class__.__name__ if obj is not None else "NoneType"
        return type_name, self.dumps(obj)

    def loads_typed(self, type_name: str, data: bytes) -> Any:
        """Lawan dari dumps_typed()."""
        return self.loads(data)
# === AKHIR PERBAIKAN ===


# === [PERBAIKAN FINAL] Class Wrapper (v3 - Memperbaiki TypeError __init__) ===
class AsyncCompatibleRedisSaver(OldRedisSaver):
    """
    Wrapper untuk OldRedisSaver yang:
    1. Mengimplementasikan metode async (aget/aput) dengan asyncio.to_thread.
    2. Memperbaiki TypeError: __init__ dengan menimpa self.serde SETELAH inisialisasi.
    """
    
    def __init__(self, *args, **kwargs):
        # === [DEBUGGING] Log tipe objek redis_client ===
        redis_client_from_kwargs = kwargs.get("redis_client")
        logger.info(f"DEBUG_PIPELINE: Menginisialisasi RedisSaver...")
        logger.info(f"DEBUG_PIPELINE: Tipe dari 'redis_client' yang diterima: {type(redis_client_from_kwargs)}")
        if hasattr(redis_client_from_kwargs, '__dict__'):
            logger.info(f"DEBUG_PIPELINE: Atribut dari 'redis_client': {list(redis_client_from_kwargs.__dict__.keys())}")
        # === AKHIR DEBUGGING ===

        # 1. Panggil __init__ dari parent class DULU.
        super().__init__(*args, **kwargs) 
        
        # 2. SEKARANG, timpa (overwrite) self.serde dengan serializer kustom kita.
        self.serde = LangChainSerializer()

    # --- Sisa fungsi async (untuk *args/**kwargs) ---
    
    async def aget_tuple(self, config: RunnableConfig, *args, **kwargs) -> Optional[CheckpointTuple]:
        return await asyncio.to_thread(self.get_tuple, config, *args, **kwargs)

    async def aput_tuple(self, config: RunnableConfig, checkpoint: CheckpointTuple, *args, **kwargs) -> None:
        await asyncio.to_thread(self.put_tuple, config, checkpoint, *args, **kwargs)

    async def aget(self, config: RunnableConfig, *args, **kwargs) -> Optional[dict]:
        return await asyncio.to_thread(self.get, config, *args, **kwargs)

    async def aput(self, config: RunnableConfig, checkpoint: dict, *args, **kwargs) -> None:
        await asyncio.to_thread(self.put, config, checkpoint, *args, **kwargs)
# === AKHIR PERBAIKAN ===


logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

tool_executor = ToolExecutor(tool_registry=TOOL_REGISTRY_INSTANCE)
rag_embedding_service = GeminiEmbeddingService()

# Inisialisasi Tokenizer (NFR Poin 8 - Token Counting)
try:
    TOKENIZER = tiktoken.get_encoding("cl100k_base")
    def _count_tokens(text: str) -> int:
        if not text: return 0
        return len(TOKENIZER.encode(text))
    def _count_message_tokens(messages: List[BaseMessage]) -> int:
        count = 0
        for msg in messages:
            if msg.content:
                count += _count_tokens(msg.content)
        return count
except Exception:
    logger.warning("Tiktoken (cl100k_base) tidak ditemukan. Estimasi token tidak akan akurat.")
    def _count_tokens(text: str) -> int:
        if not text: return 0
        return len(text) // 4 # Estimasi kasar

# --- Konstanta Manajemen Konteks (v3.0) ---
CONTEXT_WINDOW_TOKEN_LIMIT = 8000
RECENT_MESSAGES_TO_KEEP = 10

# --- Node Sanitasi (v3.0 - Perbaikan Gap #5) ---
def sanitize_input(state: AgentState) -> Dict[str, Any]:
    """
    Node #0: Membersihkan input pengguna sebelum diproses.
    (Implementasi NFR Poin 3: Sanitasi Input PII)
    """
    request_id = state.get("request_id")
    logger.info(f"REQUEST_ID: {request_id} - Node: sanitize_input")
    
    user_message = state.get("user_message", "")
    
    # [PERBAIKAN v3.0] Regex yang lebih kuat untuk PII (NFR Poin 3)
    sanitized_message = re.sub(r"[\w\.-]+@[\w\.-]+\.\w+", "[EMAIL_DIREDAKSI]", user_message, flags=re.IGNORECASE)
    sanitized_message = re.sub(r"(\+62|62|0)8[1-9][0-9]{7,10}\b", "[TELEPON_DIREDAKSI]", sanitized_message)
    sanitized_message = re.sub(r"\b\d{16}\b", "[NIK_DIREDAKSI]", sanitized_message)
    
    if sanitized_message != user_message:
        logger.warning(f"REQUEST_ID: {request_id} - Input disanitasi (PII terdeteksi).")
    
    return {"user_message": sanitized_message}

# --- Node Manajemen Konteks (v3.0 - Implementasi 'chatgpt flow') ---

async def load_full_history(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Node #A: [v3.0] Memuat SEMUA riwayat dari DB.
    """
    request_id = state.get("request_id")
    logger.info(f"REQUEST_ID: {request_id} - Node: load_full_history")
    
    dependencies = config["configurable"]["dependencies"]
    auth_info: "AuthInfoDep" = dependencies["auth_info"]
    client = auth_info["client"]
    user_id = UUID(state.get("user_id"))
    conversation_id = UUID(state.get("conversation_id"))

    try:
        messages_data = await message_queries.get_all_conversation_messages(
            client, user_id, conversation_id, limit=1000 # (Ambil 1000)
        )
        
        history: List[BaseMessage] = []
        for msg in messages_data: # (Sudah diurutkan asc)
            if msg['role'] == 'user':
                history.append(HumanMessage(content=msg.get("content", "")))
            elif msg['role'] == 'assistant':
                history.append(AIMessage(content=msg.get("content", "")))
        
        history.append(HumanMessage(content=state.get("user_message")))
        
        return {"chat_history": history}
    except Exception as e:
        logger.error(f"REQUEST_ID: {request_id} - Gagal memuat riwayat penuh: {e}")
        return {"errors": state.get("errors", []) + [{"node": "load_full_history", "error": str(e)}]}

async def manage_context_window(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Node #B: [v3.0] Mengimplementasikan logika Pruning P1-P4 (Goal 'chatgpt flow').
    """
    request_id = state.get("request_id")
    logger.info(f"REQUEST_ID: {request_id} - Node: manage_context_window")
    
    full_history = state.get("chat_history", [])
    total_tokens = _count_message_tokens(full_history)
    
    if total_tokens <= CONTEXT_WINDOW_TOKEN_LIMIT:
        logger.info(f"REQUEST_ID: {request_id} - Konteks muat ({total_tokens} tokens). Melewatkan pruning.")
        return {"total_tokens": total_tokens} # Lanjutkan

    # --- Konteks Terlalu Panjang -> Lakukan Pruning Cerdas (P1-P4) ---
    logger.warning(f"REQUEST_ID: {request_id} - Konteks terlalu panjang ({total_tokens} tokens). Memulai pruning cerdas...")
    
    messages_to_keep_recent = full_history[-RECENT_MESSAGES_TO_KEEP:]
    messages_to_evaluate = full_history[:-RECENT_MESSAGES_TO_KEEP]

    eval_json = [{"index": i, "role": msg.type, "content": msg.content} for i, msg in enumerate(messages_to_evaluate)]
    
    try:
        prompt = CONTEXT_PRUNING_PROMPT.format(messages_json=json.dumps(eval_json, indent=2))
        llm = llm_flash_client.get_llm().with_structured_output(PruningResult)
        result: PruningResult = await llm.ainvoke([HumanMessage(content=prompt)], config=config)
        
        pruned_history: List[BaseMessage] = []
        messages_to_summarize: List[BaseMessage] = [] # (P2)
        
        priority_map = {p.index: p.priority for p in result.prioritized_messages}
        
        for i, msg in enumerate(messages_to_evaluate):
            priority = priority_map.get(i)
            if priority == "P1":
                pruned_history.append(msg)
            elif priority == "P2":
                messages_to_summarize.append(msg)
            # (P3 dibuang)

        final_pruned_history = pruned_history + messages_to_keep_recent
        final_tokens = _count_message_tokens(final_pruned_history)

        logger.info(f"REQUEST_ID: {request_id} - Pruning selesai. Menyimpan {len(pruned_history)} (P1) + {len(messages_to_keep_recent)} (P4) pesan. Menyiapkan {len(messages_to_summarize)} (P2) untuk diringkas.")

        return {
            "chat_history": final_pruned_history,
            "messages_to_summarize": messages_to_summarize,
            "total_tokens": final_tokens
        }

    except Exception as e:
        logger.error(f"REQUEST_ID: {request_id} - Gagal di context_pruning: {e}. Fallback ke pemotongan 'bodoh'.")
        final_pruned_history = full_history[-RECENT_MESSAGES_TO_KEEP:]
        return {
            "chat_history": final_pruned_history,
            "total_tokens": _count_message_tokens(final_pruned_history)
        }

async def summarize_context(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Node #C: [v3.0] Meringkas pesan P2 (jika ada) dan menyimpannya ke DB.
    (Perbaikan Gap #7)
    """
    request_id = state.get("request_id")
    messages_to_summarize = state.get("messages_to_summarize", [])
    
    if not messages_to_summarize:
        logger.info(f"REQUEST_ID: {request_id} - Node: summarize_context (Dilewati, tidak ada pesan P2)")
        return {} # Tidak ada yang perlu diringkas

    logger.info(f"REQUEST_ID: {request_id} - Node: summarize_context (Meringkas {len(messages_to_summarize)} pesan P2)")
    
    dependencies = config["configurable"]["dependencies"]
    auth_info: "AuthInfoDep" = dependencies["auth_info"]
    client = auth_info["client"]
    user_id = UUID(state.get("user_id"))
    conversation_id = UUID(state.get("conversation_id"))
    
    try:
        transcript = "\n".join([f"{msg.type}: {msg.content}" for msg in messages_to_summarize])
        prompt = CONTEXT_SUMMARIZATION_PROMPT.format(messages_to_summarize=transcript)
        
        llm = llm_flash_client.get_llm()
        result = await llm.ainvoke([HumanMessage(content=prompt)], config=config)
        summary_text = result.content
        
        if summary_text:
            # [PERBAIKAN Gap #7] Simpan ke DB
            logger.info(f"REQUEST_ID: {request_id} - Menyimpan ringkasan P2 baru ke summary_memory.")
            
            await context_queries.create_summary_for_conversation(
                client, user_id, conversation_id, summary_text
            )
        
        return {}
    except Exception as e:
        logger.error(f"REQUEST_ID: {request_id} - Gagal di summarize_context: {e}")
        return {"errors": state.get("errors", []) + [{"node": "summarize_context", "error": str(e)}]}


# --- Node Klasifikasi & RAG (Diperbarui dengan Reranker Gemini) ---

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
            
            llm = llm_flash_client.get_llm().with_structured_output(IntentClassification)
            result: IntentClassification = await llm.ainvoke([HumanMessage(content=prompt)], config=config)
            
            # [PERBAIKAN] Tambahkan pengecekan jika LLM gagal setelah retry
            if not result:
                logger.error(f"REQUEST_ID: {request_id} - Panggilan LLM di classify_intent mengembalikan None. Fallback ke simple_chat.")
                return {
                    "intent": "simple_chat", # Fallback aman
                    "potential_preference": False,
                    "errors": state.get("errors", []) + [{"node": "classify_intent", "error": "LLM returned None after retries"}]
                }
            # === AKHIR PERBAIKAN ===
            
            output_tokens = _count_tokens(result.model_dump_json())
            cost = state.get("cost_estimate", 0.0)

            span.set_attributes({
                "app.intent": result.intent,
                "app.input_tokens": input_tokens, "app.output_tokens": output_tokens
            })
            
            return {
                "intent": result.intent,
                "potential_preference": result.potential_preference,
                "cost_estimate": cost,
                "output_token_count": state.get("output_token_count", 0) + output_tokens,
                "input_token_count": state.get("input_token_count", 0) + input_tokens
            }
        except Exception as e:
            logger.error(f"REQUEST_ID: {request_id} - Gagal di classify_intent: {e}", exc_info=True)
            span.set_status(trace.StatusCode.ERROR, f"Error: {e}")
            raise

        
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def query_transform(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """Node #4: Mengoptimalkan kueri pengguna menjadi kueri RAG."""
    request_id = state.get("request_id")
    logger.info(f"REQUEST_ID: {request_id} - Node: query_transform")
    
    with tracer.start_as_current_span("query_transform") as span:
        try:
            prompt = QUERY_TRANSFORM_PROMPT.format(
                chat_history=state.get("chat_history", []),
                user_message=state.get("user_message", "")
            )
            input_tokens = _count_tokens(prompt)
            
            llm = llm_flash_client.get_llm().with_structured_output(RagQueryTransform)
            result: RagQueryTransform = await llm.ainvoke([HumanMessage(content=prompt)], config=config)
            
            output_tokens = _count_tokens(result.model_dump_json())
            cost = state.get("cost_estimate", 0.0) # + ...

            span.set_attributes({ "app.rag_query": result.rag_query, "app.ts_query": result.ts_query })
            return {
                "rag_query": result.rag_query,
                "ts_query": result.ts_query,
                "cost_estimate": cost,
                "output_token_count": state.get("output_token_count", 0) + output_tokens,
                "input_token_count": state.get("input_token_count", 0) + input_tokens
            }
        except Exception as e:
            logger.error(f"REQUEST_ID: {request_id} - Gagal di query_transform: {e}", exc_info=True)
            span.set_status(trace.StatusCode.ERROR, f"Error: {e}")
            ts_query_fallback = " & ".join(state.get("user_message", "").split()[:5])
            return { "rag_query": state.get("user_message"), "ts_query": ts_query_fallback }

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def retrieve_context(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Node #5: [PERBAIKAN v3.0] Memanggil RPC RAG Holistik baru. (Perbaikan Gap #6)
    """
    request_id = state.get("request_id")
    logger.info(f"REQUEST_ID: {request_id} - Node: retrieve_context (Holistik v3.0)")
    
    rag_query = state.get("rag_query")
    ts_query = state.get("ts_query")
    user_id = UUID(state.get("user_id"))
    
    with tracer.start_as_current_span("retrieve_context") as span:
        try:
            db_client = await get_supabase_admin_async_client()
            
            embedding = await rag_embedding_service.generate_embedding(
                rag_query, task_type="retrieval_query"
            )
            span.set_attribute("app.rag.embedding_generated", True)

            # [PERBAIKAN Gap #6] Panggil RPC RAG Holistik baru
            summaries_task = context_queries.find_relevant_summaries(
                db_client, user_id, embedding, ts_query, p_match_count=10
            )
            blocks_task = db_client.rpc(
                "rpc_find_relevant_blocks_holistic",
                {
                    "p_user_id": str(user_id), 
                    "p_query_embedding": embedding, 
                    "p_query_text": ts_query, 
                    "p_limit": 20
                }
            ).execute()
            
            summaries_resp, blocks_resp = await asyncio.gather(summaries_task, blocks_task)
            
            summaries = summaries_resp or []
            blocks = blocks_resp.data or []
            
            retrieved_docs, provenance = [], []
            
            for doc in summaries:
                source_id = f"summary_id_{doc['summary_id']}"
                retrieved_docs.append({"source_id": source_id, "content": doc['summary_text'], "rank": doc.get('rank', 0.7)})
                provenance.append(doc)
                
            for doc in blocks:
                source_id = doc.get("source_id", "block_id_unknown")
                retrieved_docs.append(doc)
                provenance.append(doc)

            retrieved_docs.sort(key=lambda x: x['rank'], reverse=True)
            span.set_attribute("app.retrieved_doc_count", len(retrieved_docs))
            
            return {
                "retrieved_docs": retrieved_docs,
                "provenance": provenance
            }
            
        except Exception as e:
            logger.error(f"REQUEST_ID: {request_id} - Gagal di retrieve_context: {e}", exc_info=True)
            span.set_status(trace.StatusCode.ERROR, f"Error: {e}")
            return {"retrieved_docs": [], "provenance": []}

async def rerank_context(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Node #6: [PERBAIKAN v3.0] Menggunakan LLM Flash sebagai Reranker.
    (Perbaikan Gap #2)
    """
    request_id = state.get("request_id")
    logger.info(f"REQUEST_ID: {request_id} - Node: rerank_context (Gemini Flash Rerank)")
    
    rag_query = state.get("rag_query")
    retrieved_docs = state.get("retrieved_docs", [])
    
    if not retrieved_docs:
        return {"reranked_docs": []}

    with tracer.start_as_current_span("rerank_context_gemini") as span:
        try:
            # [BARU v3.0] Format dokumen untuk LLM
            docs_with_index = []
            for i, doc in enumerate(retrieved_docs):
                # Ambil konten (bisa 'content' atau 'summary_text')
                content = doc.get("content", doc.get("summary_text", ""))
                docs_with_index.append({
                    "index": i, # Sertakan index asli
                    "content": content,
                    "source_id": doc.get("source_id", "unknown")
                })
            
            prompt = RERANK_GEMINI_PROMPT.format(
                rag_query=rag_query,
                retrieved_docs_json=json.dumps(docs_with_index, indent=2)
            )
            input_tokens = _count_tokens(prompt)
            
            llm = llm_flash_client.get_llm().with_structured_output(RerankedDocuments)
            result: RerankedDocuments = await llm.ainvoke([HumanMessage(content=prompt)], config=config)
            
            output_tokens = _count_tokens(result.model_dump_json())
            cost = state.get("cost_estimate", 0.0) # + ...

            # Petakan kembali hasil reranking
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
                "reranked_docs": final_docs,
                "cost_estimate": cost,
                "output_token_count": state.get("output_token_count", 0) + output_tokens,
                "input_token_count": state.get("input_token_count", 0) + input_tokens
            }
            
        except Exception as e:
            logger.error(f"REQUEST_ID: {request_id} - Gagal di rerank_context (Gemini): {e}", exc_info=True)
            span.set_status(trace.StatusCode.ERROR, f"Error: {e}")
            # Fallback (NFR Poin 4) - Gunakan hasil RRF asli
            return {"reranked_docs": retrieved_docs[:5]}

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def context_compression(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """Node #7: Mengompres dokumen RAG menjadi satu string."""
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
            
            llm = llm_flash_client.get_llm()
            result = await llm.ainvoke([HumanMessage(content=prompt)], config=config)
            compressed_context = result.content if result.content else ""
            
            output_tokens = _count_tokens(compressed_context)
            cost = state.get("cost_estimate", 0.0) # + ...

            span.set_attributes({"app.input_tokens": input_tokens, "app.output_tokens": output_tokens})
            return {
                "compressed_context": compressed_context, 
                "cost_estimate": cost,
                "output_token_count": state.get("output_token_count", 0) + output_tokens,
                "input_token_count": state.get("input_token_count", 0) + input_tokens
            }
            
        except Exception as e:
            logger.error(f"REQUEST_ID: {request_id} - Gagal di context_compression: {e}", exc_info=True)
            span.set_status(trace.StatusCode.ERROR, f"Error: {e}")
            return {"compressed_context": "(Gagal memproses konteks RAG.)"}

# --- Node Agen & Tools (Diperbarui) ---

async def agent_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Node #2: [PERBAIKAN v3.0] Menggunakan .astream() dan mengakumulasi.
    (Perbaikan Gap #6 - Streaming)
    """
    request_id = state.get("request_id")
    logger.info(f"REQUEST_ID: {request_id} - Node: agent_node (Streaming v3.0)")
    
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
            
            llm_with_tools = llm_pro_client.get_llm().bind_tools(TOOL_REGISTRY_INSTANCE.values())
            
            # [PERBAIKAN v3.0 - Tugas 2]
            stream = llm_with_tools.astream(messages, config=config)
            
            final_message: Optional[AIMessage] = None
            async for chunk in stream:
                if final_message is None:
                    final_message = chunk
                else:
                    final_message += chunk # Gabungkan chunk
            # === AKHIR PERBAIKAN ===
            
            if final_message is None:
                final_message = AIMessage(content="Maaf, saya tidak dapat merespons.")

            output_tokens = _count_tokens(final_message.content)
            cost = state.get("cost_estimate", 0.0) # + ...
            span.set_attributes({"app.output_tokens": output_tokens})

            return {
                "chat_history": state.get("chat_history", []) + [final_message],
                "cost_estimate": cost,
                "output_token_count": state.get("output_token_count", 0) + output_tokens,
                "input_token_count": state.get("input_token_count", 0) + input_tokens,
                "final_response": final_message.content 
            }
        except Exception as e:
            logger.error(f"REQUEST_ID: {request_id} - Gagal di agent_node (streaming v3.0): {e}", exc_info=True)
            span.set_status(trace.StatusCode.ERROR, f"Error: {e}")
            return {"chat_history": state.get("chat_history", []) + [AIMessage(content=f"Error: {e}")]}

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def reflection_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """Node #X: [DIPERBAIKI] Memeriksa SEMUA tool calls untuk HiTL."""
    request_id = state.get("request_id")
    logger.info(f"REQUEST_ID: {request_id} - Node: reflection_node (HiTL Robusta)")
    
    last_message = state["chat_history"][-1]
    if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
        return {} # Tidak ada tool call, lanjutkan

    with tracer.start_as_current_span("reflection_node") as span:
        approval_request = None
        
        # [PERBAIKAN v3.0] Iterasi semua tool calls, bukan hanya [0]
        for tool_call in last_message.tool_calls:
            tool_call_json = json.dumps(tool_call)
            
            try:
                prompt = REFLECTION_PROMPT.format(tool_call_json=tool_call_json)
                llm = llm_flash_client.get_llm().with_structured_output(ToolApprovalRequest)
                result: ToolApprovalRequest = await llm.ainvoke([HumanMessage(content=prompt)], config=config)
                
                if result.approval_required:
                    logger.warning(f"REQUEST_ID: {request_id} - PERSETUJUAN DIPERLUKAN: {result.reason}")
                    approval_request = result.model_dump()
                    span.set_attribute("app.hitl_required", True)
                    break # [PERBAIKAN v3.0] Satu saja berbahaya, langsung jeda
            except Exception as e:
                logger.error(f"REQUEST_ID: {request_id} - Gagal di reflection_node: {e}", exc_info=True)
                # Fallback aman: anggap berbahaya
                approval_request = ToolApprovalRequest(
                    tool_name=tool_call.get("name", "unknown"),
                    tool_args=tool_call.get("args", {}),
                    reason=f"Gagal refleksi: {e}"
                ).model_dump()
                break

        if approval_request:
            return {
                "tool_approval_request": approval_request,
                "pending_tool_calls": last_message.tool_calls
            }
        else:
            logger.info(f"REQUEST_ID: {request_id} - Semua tools aman, melanjutkan.")
            return {"pending_tool_calls": last_message.tool_calls}

async def call_tools(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Node #3: [PERBAIKAN] Mengeksekusi tools menggunakan DI dari config.
    (Perbaikan Gap #3)
    """
    request_id = state.get("request_id")
    logger.info(f"REQUEST_ID: {request_id} - Node: call_tools")
    
    tool_calls_to_run = state.get("pending_tool_calls", [])
    if not tool_calls_to_run: return {}

    tool_messages: List[BaseMessage] = []
    
    # [PERBAIKAN Gap #3] Ambil dependensi dari config
    try:
        dependencies = config["configurable"]["dependencies"]
        auth_info: AuthInfoDep = dependencies["auth_info"]
        background_tasks: BackgroundTasks = dependencies["background_tasks"]
    except KeyError:
        logger.error(f"REQUEST_ID: {request_id} - Fatal: Dependensi tidak ditemukan di config. Tool tidak bisa dijalankan.")
        return {"errors": state.get("errors", []) + [{"node": "call_tools", "error": "Dependencies missing from config"}]}

    # Inisialisasi service yang diperlukan
    schedule_service: ScheduleService = get_schedule_service(auth_info)
    
    for tool_call in tool_calls_to_run:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        
        # Injeksi dependensi dinamis
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
    
    return {
        "chat_history": state.get("chat_history", []) + tool_messages,
        "pending_tool_calls": None
    }


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def extract_preferences_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Node #8: [PERBAIKAN] Berjalan di akhir, menggunakan DI dari config.
    (Solusi TODO #1)
    """
    request_id = state.get("request_id")
    logger.info(f"REQUEST_ID: {request_id} - Node: extract_preferences_node")
    
    if not state.get("potential_preference"):
        logger.info(f"REQUEST_ID: {request_id} - Dilewati, tidak ada potensi preferensi.")
        return {}

    with tracer.start_as_current_span("extract_preferences_node") as span:
        try:
            # [PERBAIKAN Gap #3] Ambil dependensi dari config
            dependencies = config["configurable"]["dependencies"]
            auth_info: "AuthInfoDep" = dependencies["auth_info"]
            embedding_service: "EmbeddingServiceDep" = dependencies["embedding_service"]
            
            final_ai_response = state.get("final_response", "")
            
            prompt = EXTRACT_PREFERENCES_PROMPT.format(
                user_message=state.get("user_message", ""),
                ai_response=final_ai_response
            )
            input_tokens = _count_tokens(prompt)
            
            llm = llm_flash_client.get_llm().with_structured_output(ExtractedPreference)
            result: ExtractedPreference = await llm.ainvoke([HumanMessage(content=prompt)], config=config)
            
            output_tokens = _count_tokens(result.model_dump_json())
            cost = state.get("cost_estimate", 0.0) # + ...

            span.set_attributes({
                "app.input_tokens": input_tokens,
                "app.output_tokens": output_tokens,
                "app.preferences_found": bool(result.preferences)
            })
            
            # [BARU] Langsung simpan ke DB
            if result.preferences:
                logger.info(f"REQUEST_ID: {request_id} - Menyimpan {len(result.preferences)} preferensi ke DB...")
                await save_preferences_to_db(
                    authed_client=auth_info["client"],
                    embedding_service=embedding_service,
                    user_id=UUID(state.get("user_id")),
                    preferences_list=[p.model_dump() for p in result.preferences]
                )

            return {
                "extracted_preferences": result,
                "cost_estimate": cost,
                "output_token_count": state.get("output_token_count", 0) + output_tokens,
                "input_token_count": state.get("input_token_count", 0) + input_tokens
            }
        except Exception as e:
            logger.error(f"REQUEST_ID: {request_id} - Gagal di extract_preferences_node: {e}", exc_info=True)
            span.set_status(trace.StatusCode.ERROR, f"Error: {e}")
            return {"errors": state.get("errors", []) + [{"node": "extract_preferences", "error": str(e)}]}

# --- [PERBAIKAN v3.0] Node Pengecekan Konteks (Tugas 1.2) ---
def check_context_length(state: AgentState) -> Dict[str, Any]:
    """
    Node #9: [v3.0] Memeriksa total token (Tugas 1.2).
    """
    request_id = state.get("request_id")
    logger.info(f"REQUEST_ID: {request_id} - Node: check_context_length")
    
    # [PERBAIKAN v3.0] Ambil total token dari 'manage_context_window'
    total_tokens = state.get("total_tokens", 0)
    
    return {
        "total_tokens": total_tokens
    }

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def prune_and_summarize_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Node #10: [BARU v2.9] Menerapkan P1-P4 Pruning & P2 Summarization.
    (Implementasi Tugas 1.3 & 'chatgpt flow')
    """
    request_id = state.get("request_id")
    logger.warning(f"REQUEST_ID: {request_id} - Node: prune_and_summarize_node (Konteks terlampaui!)")
    
    # (Perbaikan Gap #3 - Gunakan DI dari config)
    dependencies = config["configurable"]["dependencies"]
    auth_info: AuthInfoDep = dependencies["auth_info"]
    client = auth_info["client"]
    user_id = UUID(state.get("user_id"))
    
    full_history = state.get("chat_history", [])
    
    # (P4) Ambil 10 pesan terakhir (wajib disimpan)
    messages_to_keep_recent = full_history[-RECENT_MESSAGES_TO_KEEP:]
    messages_to_evaluate = full_history[:-RECENT_MESSAGES_TO_KEEP]

    eval_json = [{"index": i, "role": msg.type, "content": msg.content} for i, msg in enumerate(messages_to_evaluate)]
    
    with tracer.start_as_current_span("prune_and_summarize") as span:
        try:
            # 1. Panggil LLM Pruning (P1, P2, P3)
            pruning_prompt = CONTEXT_PRUNING_PROMPT.format(messages_json=json.dumps(eval_json, indent=2))
            pruning_llm = llm_flash_client.get_llm().with_structured_output(PruningResult)
            pruning_result: PruningResult = await pruning_llm.ainvoke([HumanMessage(content=pruning_prompt)], config=config)
            
            messages_to_summarize: List[BaseMessage] = [] # (P2)
            priority_map = {p.index: p.priority for p in pruning_result.prioritized_messages}
            
            for i, msg in enumerate(messages_to_evaluate):
                if priority_map.get(i) == "P2":
                    messages_to_summarize.append(msg)
            
            # 2. Panggil LLM Summarization (jika ada pesan P2)
            if messages_to_summarize:
                transcript = "\n".join([f"{msg.type}: {msg.content}" for msg in messages_to_summarize])
                summary_prompt = CONTEXT_SUMMARIZATION_PROMPT.format(messages_to_summarize=transcript)
                
                summary_llm = llm_flash_client.get_llm()
                summary_result = await summary_llm.ainvoke([HumanMessage(content=summary_prompt)], config=config)
                summary_text = summary_result.content
                
                if summary_text:
                    # [PERBAIKAN Gap #7] Simpan ke DB
                    logger.info(f"REQUEST_ID: {request_id} - Menyimpan ringkasan P2 baru ke summary_memory.")
                    
                    # TODO: Kita perlu 'context_id' lama. 
                    # Ini adalah bug baru. Kita perlu cara baru menyimpan summary per conversation.
                    # await context_queries.create_summary_for_context(
                    #     client, user_id, conversation_id, summary_text
                    # )
                    span.set_attribute("app.summary_created", True)
            
            return {} # Selesai
        
        except Exception as e:
            logger.error(f"REQUEST_ID: {request_id} - Gagal di prune_and_summarize_node: {e}", exc_info=True)
            span.set_status(trace.StatusCode.ERROR, f"Error: {e}")
            return {"errors": state.get("errors", []) + [{"node": "prune_and_summarize", "error": str(e)}]}

# --- Definisi Alur Graph (Final v3.0 - Smart Context) ---
def build_langgraph_agent():
    """Membangun LangGraph Agent v3.2 (stabil, interrupt-ready, RedisSaver kompatibel)."""
    redis_client = getattr(rate_limiter, "redis", None)
    checkpointer = AsyncCompatibleRedisSaver(redis_client=redis_client) if redis_client else None
        
    workflow = StateGraph(AgentState)

    # 1️⃣ Tambahkan Semua Node Utama
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

    # 🆕 Tambahkan node 'interrupt' di sini — SEBELUM edges dideklarasikan
    def interrupt_node(state: AgentState):
        """Menjeda graph sementara, menunggu aksi manusia (HiTL)."""
        logger.warning(f"Graph dijeda untuk request_id={state.get('request_id')}")
        return state
    workflow.add_node("interrupt", interrupt_node)

    # 2️⃣ Entry Point
    workflow.set_entry_point("sanitize_input")
    workflow.add_edge("sanitize_input", "load_full_history")
    workflow.add_edge("load_full_history", "manage_context_window")

    # Router #1
    def route_after_context_management(state: AgentState) -> str:
        """
        Memutuskan apakah perlu meringkas konteks atau langsung ke klasifikasi.
        """
        if state.get("messages_to_summarize"):
            return "summarize_context"
        return "classify_intent"

    workflow.add_conditional_edges(
        "manage_context_window",
        route_after_context_management,
        {
            "summarize_context": "summarize_context", 
            "classify_intent": "classify_intent"
        },
    )

    workflow.add_edge("summarize_context", "classify_intent")

    # Router #2
    def route_after_classify(state: AgentState) -> str:
        if state.get("errors"):
            return END
        intent = state.get("intent")
        return "query_transform" if intent == "rag_query" else "agent_node"

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

    # Router #3
    def route_after_agent(state: AgentState) -> str:
        if state.get("errors"):
            return END
        last_message = state["chat_history"][-1]
        return (
            "reflection_node"
            if isinstance(last_message, AIMessage) and getattr(last_message, "tool_calls", None)
            else "extract_preferences_node"
        )

    workflow.add_conditional_edges(
        "agent_node",
        route_after_agent,
        {
            "reflection_node": "reflection_node",
            "extract_preferences_node": "extract_preferences_node",
            "__end__": END,
        },
    )

    # Router #4 (HiTL / reflection)
    def route_after_reflection(state: AgentState) -> str:
        if state.get("errors"):
            return END
        if state.get("tool_approval_request"):
            logger.warning(f"REQUEST_ID={state.get('request_id')} → Graph dijeda menunggu persetujuan.")
            return "interrupt"
        else:
            return "call_tools"

    workflow.add_conditional_edges(
        "reflection_node",
        route_after_reflection,
        {"call_tools": "call_tools", "interrupt": "interrupt"},
    )

    # Edge Loop
    workflow.add_edge("call_tools", "agent_node")

    # Akhir
    workflow.add_edge("extract_preferences_node", "check_context_length")

    def route_check_context(state: AgentState) -> str:
        return "prune_and_summarize_node" if state.get("total_tokens", 0) > CONTEXT_WINDOW_TOKEN_LIMIT else "__end__"

    workflow.add_conditional_edges(
        "check_context_length",
        route_check_context,
        {"prune_and_summarize_node": "prune_and_summarize_node", "__end__": END},
    )
    workflow.add_edge("prune_and_summarize_node", END)

    # ✅ Kompilasi Graph
    logger.info("🔁 Mengkompilasi LangGraph Agent v3.2 (interrupt-ready)...")
    return workflow.compile(checkpointer=checkpointer) if checkpointer else workflow.compile()


compiled_langgraph_agent = build_langgraph_agent()
