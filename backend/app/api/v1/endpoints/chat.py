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
from app.services.chat_engine.chat_service import ChatService

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

# --- Endpoint Chat (Refactored v3.2) ---
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
    Menggunakan arsitektur LangGraph v3.2 dengan service layer.
    """
    user = auth_info["user"]
    client = auth_info["client"]

    logger.warning(f"Memulai LangGraph v3.2 (Streaming) untuk user {user.id}...")
    
    # FIX: Remove 'await' - async generator is used directly
    stream_generator = ChatService.create_chat_stream(
        user=user,
        client=client,
        message=request.message,
        conversation_id=request.conversation_id,
        background_tasks=background_tasks,
        embedding_service=embedding_service,
        langgraph_agent=langgraph_agent
    )
    
    return StreamingResponse(stream_generator, media_type="application/x-ndjson")

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
                detail=f"Error di stream_conversation_title: {str(e)}",
                status_code=500
            )
            yield error_payload.model_dump_json() + "\n"
    
    return StreamingResponse(stream_generator(), media_type="application/x-ndjson")

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
    """Endpoint untuk memperbarui judul conversation secara manual."""
    user = auth_info["user"]
    client = auth_info["client"]
    
    try:
        updated_convo = await conversation_queries.update_conversation_title(
            client=client,
            user_id=user.id,
            conversation_id=conversation_id,
            new_title=payload.title
        )
        
        if not updated_convo:
            raise NotFoundError(f"Conversation {conversation_id} tidak ditemukan.")
        
        return ConversationListItem(
            conversation_id=updated_convo["conversation_id"],
            title=updated_convo["title"],
            last_message_at=updated_convo["last_message_at"],
            created_at=updated_convo["created_at"],
            message_count=updated_convo.get("message_count", 0)
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Gagal memperbarui judul conversation {conversation_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )