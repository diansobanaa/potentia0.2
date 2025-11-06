# backend\app\api\v1\endpoints\chat.py
import logging
import json # <-- IMPOR YANG DIPERLUKAN
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from fastapi.responses import StreamingResponse # <-- IMPOR YANG HILANG
from typing import AsyncGenerator # <-- IMPOR YANG DIPERLUKAN
from app.core.dependencies import (
    AuthInfoDep, 
    EmbeddingServiceDep, 
    JudgeChainDep,
    ConversationListServiceDep,
    ConversationMessagesServiceDep,
    StreamingTitleServiceDep # <-- IMPOR BARU
)
from app.services.chat_service import ChatService
from app.services.conversation_messages_service import ConversationMessagesService
from app.services.title_stream_service import TitleStreamService # <-- IMPOR BARU

from app.services.chat_engine.schemas import (ChatRequest, 
    ChatResponse, 
    JudgeDecision, 
    PaginatedConversationListResponse, 
    PaginatedMessageListResponse,
    ConversationTitleUpdate,
    ConversationListItem
    )
from app.db.queries.conversation import conversation_queries
# Impor skema stream (dari langkah kita sebelumnya)
from app.services.chat_engine.streaming_schemas import StreamError 

from app.core.exceptions import DatabaseError, NotFoundError
from uuid import UUID

router = APIRouter()
logger = logging.getLogger(__name__)

 
@router.post("/", response_model=ChatResponse)
async def handle_chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    auth_info: AuthInfoDep,
    embedding_service: EmbeddingServiceDep,
    judge_chain: JudgeChainDep
):
    """
    Endpoint utama (JSON non-streaming) untuk semua interaksi chat pengguna.
    
    """
    try:
        chat_service = ChatService(auth_info, embedding_service, judge_chain)
        
        final_response: ChatResponse = await chat_service.handle_chat_turn_full_pipeline(
            request, background_tasks
        )
        
        return final_response
    
    except DatabaseError as e:
        error_message = str(e) 
        logger.error(f"DatabaseError saat chat: {error_message}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_message)
    except Exception as e:
        error_message = str(e)
        logger.error(f"Error tidak terduga di endpoint chat: {error_message}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal server error: {error_message}")



@router.get("/conversations-list", response_model=PaginatedConversationListResponse)
async def list_conversations(
    conversation_service: ConversationListServiceDep, 
    page: int = Query(1, ge=1, description="Nomor halaman, dimulai dari 1"),
    size: int = Query(20, ge=1, le=100, description="Jumlah item per halaman (maks 100)")
):
    """
    Endpoint untuk mendapatkan daftar conversation pengguna dengan pagination.
   
    """
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
    """
    Endpoint untuk mendapatkan daftar pesan untuk satu conversation_id.
   
    """
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
    summary="Stream Judul Percakapan (Real-time)",
    description="""
Endpoint ini HANYA men-stream judul percakapan yang dibuat oleh AI 
secara kata-demi-kata.

Frontend harus memanggil ini secara paralel atau setelah menerima 
respons dari `POST /chat` untuk mengisi judul di sidebar 
secara real-time.

Mengembalikan stream **ndjson** (Newline Delimited JSON).
"""
)
async def stream_conversation_title(
    conversation_id: UUID,
    title_service: StreamingTitleServiceDep, # <-- Menggunakan Dependency
) -> StreamingResponse: # <-- Tipe respons yang menyebabkan error
    """
    Menangani logika untuk streaming judul.
    """
    
    async def stream_generator() -> AsyncGenerator[str, None]:
        """Generator internal untuk streaming judul."""
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


# --- TAMBAHKAN ENDPOINT BARU DI SINI ---

@router.patch(
    "/conversations/{conversation_id}",
    response_model=ConversationListItem, # Menggunakan skema yang ada untuk respons
    summary="Perbarui Judul Percakapan (Manual)",
    description="Endpoint ini digunakan untuk memperbarui judul percakapan secara manual."
)
async def update_conversation_title_manual(
    conversation_id: UUID,
    payload: ConversationTitleUpdate, # Skema body dari Langkah 1
    auth_info: AuthInfoDep, 
):
    """
    Memperbarui judul percakapan secara manual.
    """
    user = auth_info["user"]
    client = auth_info["client"]
    
    try:
        # Memanggil fungsi query dari Langkah 2
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