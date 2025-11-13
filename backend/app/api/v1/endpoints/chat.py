# File: backend\app\api\v1\endpoints\chat.py
# (Final v3.2 - Menghapus duplikasi fungsi & impor v1)

import logging
import json
import uuid
from uuid   import UUID, uuid4
from xmlrpc import client
import tiktoken
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator, List
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import HumanMessage, BaseMessage, AIMessage, AIMessageChunk, ToolMessage

from app.core.dependencies import (
    AuthInfoDep, 
    EmbeddingServiceDep, 
    ConversationListServiceDep,
    ConversationMessagesServiceDep,
    StreamingTitleServiceDep,
    LangGraphAgentDep 
)
# [HAPUS v3.2] Hapus impor v1
# from app.services.chat_service import ChatService 
# from app.core.dependencies import JudgeChainDep 

from app.models.user import User, SubscriptionTier
from app.services.chat_engine.agent_state import AgentState 
from app.services.chat_engine.schemas import (ChatRequest, ChatResponse, 
                                              PaginatedConversationListResponse, PaginatedMessageListResponse,
                                              ConversationTitleUpdate, ConversationListItem)
from app.db.queries.conversation import message_queries, conversation_queries, message_list_queries
from app.core.config import settings
from app.services.chat_engine.streaming_schemas import StreamError
from app.core.exceptions import DatabaseError, NotFoundError

router = APIRouter()
logger = logging.getLogger(__name__)

# Inisialisasi Tokenizer
try:
    TOKENIZER = tiktoken.get_encoding("cl100k_base")
    def _count_tokens(text: str) -> int:
        if not text: return 0
        return len(TOKENIZER.encode(text))
except Exception:
    logger.warning("Tiktoken (cl100k_base) tidak ditemukan. Estimasi token tidak akan akurat.")
    def _count_tokens(text: str) -> int:
        if not text: return 0
        return len(text) // 4

# --- Helper Pemuat Riwayat (v3.2) ---
async def get_chat_history(client, user_id, conversation_id) -> List[BaseMessage]:
    """
    (v3.2) Helper untuk memuat riwayat pesan (context window "bodoh" sementara).
    Menggantikan node 'load_full_history' untuk sementara.
    """
    if not conversation_id: return []
    try:
        # [PERBAIKAN Tugas 1.2] Gunakan limit=40
        messages_data, _ = await message_list_queries.get_conversation_messages_paginated(
            client, user_id, conversation_id, offset=0, limit=40 
        )
        
        history: List[BaseMessage] = []
        for msg in sorted(messages_data, key=lambda x: x['created_at']):
            content = msg.get("content", "")
            if msg['role'] == 'user':
                history.append(HumanMessage(content=content))
            elif msg['role'] == 'assistant':
                tool_calls = msg.get("tool_calls") 
                if tool_calls:
                    history.append(AIMessage(content=content, tool_calls=tool_calls))
                else:
                    history.append(AIMessage(content=content))
        return history
    except Exception as e:
        logger.error(f"Gagal memuat riwayat (v3.2) untuk {conversation_id}: {e}")
        return []

# --- Helper Pemuat Izin (v3.2) ---
def _get_user_permissions(user: User) -> List[str]:
    """
    (v3.2) Memuat daftar izin (scopes) berdasarkan role pengguna.
    (Implementasi NFR Poin 3 - Perbaikan Gap #2)
    """
    base_permissions = ["tool:search_online"]
    
    tier = user.subscription_tier
    
    if tier == SubscriptionTier.pro or tier == SubscriptionTier.admin:
        base_permissions.extend([
            "tool:create_schedule_tool",
            "tool:create_canvas_block"
        ])
    if tier == SubscriptionTier.admin:
        base_permissions.append("tool:admin_access")
        
    logger.debug(f"Izin dimuat untuk user {user.id}: {base_permissions}")
    return base_permissions

# --- Endpoint Chat (Final v3.2) ---
@router.post("/")
async def handle_chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    auth_info: AuthInfoDep,
    embedding_service: EmbeddingServiceDep, 
    langgraph_agent: LangGraphAgentDep 
) -> StreamingResponse:
    """
    Endpoint utama (STREAMING) untuk semua interaksi chat pengguna.
    Menggunakan arsitektur LangGraph v3.2.
    """
    
    user = auth_info["user"]
    client = auth_info["client"]

    # [FINAL] Kita asumsikan 100% trafik ke v3.2
    logger.warning(f"Memulai LangGraph v3.2 (Streaming) untuk user {user.id}...")
    
    request_id = str(uuid.uuid4())
    conversation_id = request.conversation_id or uuid.uuid4()

    async def v2_stream_generator() -> AsyncGenerator[str, None]:
        final_ai_response_chunks = []
        final_state_snapshot = None
        total_output_tokens = 0
        current_node = None
        
        try:
            # Pastikan baris 'conversations' ada (Perbaikan Bug v2.8)
            await conversation_queries.get_or_create_conversation(
                client,
                user.id,
                conversation_id
            )

            chat_history = await get_chat_history(client, user.id, conversation_id)
            
            permissions = _get_user_permissions(user)
            
            initial_state = AgentState(
                request_id=request_id,
                trace_id=None, 
                user_id=str(user.id),
                permissions=permissions,
                conversation_id=str(conversation_id),
                created_at=datetime.utcnow(),
                user_message=request.message,
                chat_history=chat_history + [HumanMessage(content=request.message)], 
                cost_estimate=0.0,
                input_token_count=0,
                output_token_count=0
                # ... sisa state akan diisi oleh graph
            )
            
            # Inject dependensi ke config (Perbaikan Gap #3)
            config = RunnableConfig(
                configurable={
                    "thread_id": str(conversation_id),
                    "dependencies": {
                        "auth_info": auth_info,
                        "embedding_service": embedding_service,
                        "background_tasks": background_tasks
                    }
                }
            )
            
            current_node = None
            async for event in langgraph_agent.astream_events(initial_state, config=config, version="v1"):
                kind = event["event"]
                
                # Kirim status 'Thinking...'
                if kind == "on_chain_start":
                    node_name = event["name"]
                    current_node = node_name
                    if node_name == "classify_intent":
                        yield json.dumps({"type": "status", "payload": "Menganalisis niat..."}) + "\n"
                    elif node_name == "query_transform":
                        yield json.dumps({"type": "status", "payload": "Memperjelas kueri..."}) + "\n"
                    elif node_name == "retrieve_context":
                        yield json.dumps({"type": "status", "payload": "Mencari ingatan..."}) + "\n"
                    elif node_name == "rerank_context":
                        yield json.dumps({"type": "status", "payload": "Memfilter ingatan..."}) + "\n"
                    elif node_name == "context_compression":
                        yield json.dumps({"type": "status", "payload": "Meringkas ingatan..."}) + "\n"
                    elif node_name == "agent_node":
                        yield json.dumps({"type": "status", "payload": "Merumuskan jawaban..."}) + "\n"
                
                # Menangani streaming token (NFR Poin 8)
                elif kind == "on_chat_model_stream":
                    # [PERBAIKAN] Hanya kirim token jika berasal dari 'agent_node'
                    if current_node == "agent_node":
                        chunk = event["data"]["chunk"]
                        if isinstance(chunk, AIMessageChunk) and chunk.content:
                            token = chunk.content
                            final_ai_response_chunks.append(token)
                            total_output_tokens += _count_tokens(token)
                            yield json.dumps({"type": "token_chunk", "payload": token}) + "\n"
                elif kind == "on_chain_end":
                    current_node = None
                    node_name = event["name"]
                    output_data = event["data"]["output"]
                    
                    if node_name == "reflection_node":
                        # Menangani HiTL (NFR Poin 11)
                        if output_data.get("tool_approval_request"):
                            logger.warning(f"REQUEST_ID: {request_id} - Graph DIJEDA, mengirim permintaan persetujuan.")
                            yield json.dumps({
                                "type": "tool_approval_required",
                                "payload": output_data["tool_approval_request"]
                            }) + "\n"
                    
                    elif node_name == "call_tools":
                        last_tool_msg: ToolMessage = output_data["chat_history"][-1]
                        yield json.dumps({
                            "type": "status",
                            "payload": f"Mendapatkan hasil: {str(last_tool_msg.content)[:50]}..."
                        }) + "\n"
                
                elif kind == "on_graph_end":
                    final_state_snapshot = event["data"]["output"]

            # --- Tugas Latar Belakang (Setelah stream selesai) ---
            logger.info(f"REQUEST_ID: {request_id} - Stream v3.2 selesai.")
            
            if not final_state_snapshot:
                logger.error(f"REQUEST_ID: {request_id} - Graph selesai tapi tidak ada state akhir!")
                return

            # [HAPUS v3.2] Penyimpanan pesan sekarang ditangani di dalam 'check_context_length'
            # background_tasks.add_task(...)
            
        except Exception as e:
            logger.error(f"Error tidak terduga di stream v3.2 (req_id: {request_id}): {e}", exc_info=True)
            error_payload = StreamError(detail=f"v3.2 Stream Error: {e}", status_code=500)
            yield error_payload.model_dump_json() + "\n"

    return StreamingResponse(v2_stream_generator(), media_type="application/x-ndjson")

# --- ENDPOINT A: DAFTAR CONVERSATION & PESAN DENGAN PAGINASI ---
@router.get("/conversations-list", response_model=PaginatedConversationListResponse)
async def list_conversations(
    conversation_service: ConversationListServiceDep, 
    page: int = Query(1, ge=1, description="Nomor halaman, dimulai dari 1"),
    size: int = Query(20, ge=1, le=100, description="Jumlah item per halaman (maks 100)")
):
    try:
        paginated_response = await conversation_service.get_paginated_conversations(page=page, size=size)
        return paginated_response
    except Exception as e:
        error_message = f"Gagal mengambil daftar conversation: {str(e)}"
        logger.error(error_message, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Terjadi kesalahan pada server saat mengambil data."
        )
    
    
@router.get("/{conversation_id}/messages", response_model=PaginatedMessageListResponse)
async def list_messages(
    conversation_id: UUID,
    messages_service: ConversationMessagesServiceDep,
    page: int = Query(1, ge=1, description="Nomor halaman, dimulai dari 1"), 
    size: int = Query(5, ge=1, le=100, description="Jumlah item per halaman (maks 100)")
):
    try:
        paginated_response = await messages_service.get_paginated_messages(
            conversation_id=conversation_id, page=page, size=size
        )
        logger.info(f"paginated_response:{paginated_response}")
        return paginated_response
    except Exception as e:
        error_message = f"Gagal mengambil pesan untuk conversation {conversation_id}: {str(e)}"
        logger.error(error_message, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Terjadi kesalahan pada server saat mengambil data pesan."
        )

# --- ENDPOINT B: STREAMING JUDUL (DARI LANGKAH SEBELUMNYA) ---
    
@router.get(
    "/stream/{conversation_id}/title", 
    response_model=None,
    summary="Stream Judul Percakapan (Real-time)"
)
async def stream_conversation_title(
    conversation_id: UUID,
    title_service: StreamingTitleServiceDep,
) -> StreamingResponse:
    
    async def stream_generator() -> AsyncGenerator[str, None]:
        try:
            logger.info(f"Memulai stream judul untuk convo: {conversation_id}")
            
            async for json_chunk in title_service.orchestrate_streaming_title(conversation_id):
                yield json_chunk 

        except Exception as e:
            logger.error(f"Error tidak terduga di stream_conversation_title: {e}", exc_info=True)
            error_payload = StreamError(
                detail=f"Internal server error: {str(e)}", 
                status_code=500
            )
            yield error_payload.model_dump_json() + "\n"

    return StreamingResponse(
        stream_generator(), 
        media_type="application/x-ndjson" 
    )


# --- ENDPOINT C: UPDATE JUDUL MANUAL ---

@router.patch(
    "/conversations/{conversation_id}",
    response_model=ConversationListItem, 
    summary="Perbarui Judul Percakapan (Manual)"
)
async def update_conversation_title_manual(
    conversation_id: UUID,
    payload: ConversationTitleUpdate, 
    auth_info: AuthInfoDep, 
):
    user = auth_info["user"]
    client = auth_info["client"]
    
    try:
        updated_conversation = await conversation_queries.update_conversation_title(
            authed_client=client,
            user_id=user.id,
            conversation_id=conversation_id,
            new_title=payload.title
        )
        return updated_conversation
    
    except NotFoundError as e:
        logger.warning(f"Gagal update judul (404) untuk convo {conversation_id}: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Gagal update judul (500) untuk convo {conversation_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Error tidak terduga di update_conversation_title_manual: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Terjadi kesalahan internal.")

# [HAPUS v3.2] Hapus fungsi get_chat_history duplikat (Perbaikan Kekurangan #3)