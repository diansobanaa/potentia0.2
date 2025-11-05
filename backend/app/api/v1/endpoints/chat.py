# backend\app\api\v1\endpoints\chat.py
import logging
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from app.core.dependencies import (
    AuthInfoDep, 
    EmbeddingServiceDep, 
    JudgeChainDep,
    ConversationListServiceDep,
    ConversationMessagesServiceDep # <-- IMPOR DEPENDENCY BARU
)
from app.services.chat_service import ChatService
from app.services.conversation_messages_service import ConversationMessagesService

from app.services.chat_engine.schemas import (ChatRequest, 
    ChatResponse, 
    JudgeDecision, 
    PaginatedConversationListResponse, 
    PaginatedMessageListResponse)
from app.core.exceptions import DatabaseError, NotFoundError
from uuid import UUID

router = APIRouter()
logger = logging.getLogger(__name__)

 
@router.post("/", response_model=ChatResponse)
async def handle_chat(
    request: ChatRequest,
    # --- PERUBAHAN: Injeksi BackgroundTasks ---
    # FastAPI akan secara otomatis menyediakan objek ini
    background_tasks: BackgroundTasks,
    # --- AKHIR PERUBAHAN ---
    auth_info: AuthInfoDep,
    embedding_service: EmbeddingServiceDep,
    judge_chain: JudgeChainDep
):
    """
    Endpoint utama untuk semua interaksi chat pengguna.
    """
    try:
        chat_service = ChatService(auth_info, embedding_service, judge_chain)
        
        # --- PERUBAHAN: Meneruskan background_tasks ke service ---
        final_response: ChatResponse = await chat_service.handle_chat_turn_full_pipeline(
            request, background_tasks
        )
        # --- AKHIR PERUBAHAN ---
        
        return final_response
    
    except DatabaseError as e:
        # --- PERBAIKAN DI SINI ---
        error_message = str(e) # Gunakan str(e) bukan e.detail
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
        # Tangani error secara umum, bisa disesuaikan dengan custom exception
        error_message = f"Gagal mengambil daftar conversation: {str(e)}"
        logger.error(error_message, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Terjadi kesalahan pada server saat mengambil data."
        )
    

    
# --- ENDPOINT HALAMAN CHAT CONVERSATION ---
@router.get("/{conversation_id}/messages", response_model=PaginatedMessageListResponse)
async def list_messages(
    conversation_id: UUID,
    messages_service: ConversationMessagesServiceDep, # <-- PERBAIKAN
    page: int = Query(1, ge=1, description="Nomor halaman, dimulai dari 1"), 
    size: int = Query(5, ge=1, le=100, description="Jumlah item per halaman (maks 100)")
):
    """
    Endpoint untuk mendapatkan daftar pesan (halaman chat itu sendiri)
    untuk satu conversation_id, dipaginasi dari yang terbaru.
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