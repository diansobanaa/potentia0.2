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
from typing import AsyncGenerator, List, Optional, Literal
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import HumanMessage, BaseMessage, AIMessage, AIMessageChunk, ToolMessage
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID

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
class LLMConfig(BaseModel):
    """LLM configuration per request."""
    model: str = Field(..., description="Model identifier (e.g., 'gemini-2.5-flash')")
    temperature: Optional[float] = Field(0.2, ge=0.0, le=2.0, description="0.0-2.0")
    max_tokens: Optional[int] = Field(None, ge=1, le=32000, description="Optional max tokens")

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000, description="User message")
    conversation_id: Optional[UUID] = Field(None, description="If null → create new; else reuse if exists")
    llm_config: Optional[LLMConfig] = Field(None, description="Frontend-selected model/params")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Explain quantum computing",
                "conversation_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "llm_config": {
                    "model": "gemini-2.5-flash",
                    "temperature": 0.7
                }
            }
        }

@router.post("/", summary="Send chat message (streaming)")
async def handle_chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    auth_info: AuthInfoDep,
    embedding_service: EmbeddingServiceDep, 
    langgraph_agent: LangGraphAgentDep 
) -> StreamingResponse:
    """
    Chat endpoint with frontend-driven model selection.
    
    ## Supported Models (by provider):
    
    **Gemini (Google)**
    - `gemini-flash-lite-latest` - Fast, lightweight model
    - `gemini-2.5-pro` - Advanced reasoning and complex tasks
    - `gemini-2.5-flash` - Balanced speed and capability
    
    **OpenAI**
    - `gpt-4o-mini` - Fast GPT-4 variant
    - `gpt-5-pro` - Most advanced model
    - `gpt-4.1` - Enhanced GPT-4
    
    **DeepSeek**
    - `deepseek-chat` - General conversation
    - `deepseek-v3` - Latest version
    - `deepseek-r1` - Reasoning-focused
    
    **Kimi (Moonshot)**
    - `moonshot-v1-32k` - 32K context window
    - `moonshot-v1-8k` - 8K context window
    - `moonshot-v1-128k` - 128K context window
    - `kimi-k2-thinking` - Enhanced reasoning
    
    **XAI (Grok)**
    - `grok-4-fast-reasoning-latest` - Fast reasoning
    - `grok-4` - Standard model
    - `grok-code-fast-1` - Code-optimized
    
    ## Request Body:
    - `message`: User's message (required)
    - `conversation_id`: Conversation UUID (optional, creates new if null)
    - `llm_config`: Model configuration (optional, uses DEFAULT_MODEL if not provided)
        - `model`: Model identifier from list above
        - `temperature`: 0.0-2.0 (default: 0.2)
        - `max_tokens`: Max output tokens (optional)
    
    ## Response:
    Returns Server-Sent Events (SSE) stream with:
    - AI response chunks
    - Token usage metadata
    - Final state information
    
    Use `/models/available` to check which models are currently configured.
    """
    user = auth_info["user"]
    client = auth_info["client"]

    # Log received LLM config
    if request.llm_config:
        logger.info(
            f"🎯 Received llm_config: model={request.llm_config.model}, "
            f"temperature={request.llm_config.temperature}"
        )
    else:
        logger.info("⚠️  No llm_config provided, will use DEFAULT_MODEL")

    stream_generator = ChatService.create_chat_stream(
        user=user,
        client=client,
        message=request.message,
        conversation_id=request.conversation_id,
        background_tasks=background_tasks,
        embedding_service=embedding_service,
        langgraph_agent=langgraph_agent,
        llm_config=request.llm_config.dict() if request.llm_config else None  # pass-through
    )
    
    return StreamingResponse(stream_generator, media_type="application/x-ndjson")


@router.get("/models/available", summary="Get available models", description="""
Get list of LLM models that backend can currently support.
Models are only listed if their API keys are configured.
""")
async def get_available_models():
    """Get list of supported models based on configured API keys."""
    from app.services.chat_engine.llm_provider import get_available_models
    
    models = get_available_models()
    
    return {"available_models": models, "total_count": len(models)}

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
            client,
            user.id,
            conversation_id,
            payload.title
        )
        
        if not updated_convo:
            raise NotFoundError(f"Conversation {conversation_id} tidak ditemukan.")
        
        return ConversationListItem(
            conversation_id=updated_convo["conversation_id"],
            title=updated_convo["title"],
            updated_at=updated_convo.get("last_message_at") or updated_convo.get("updated_at") or updated_convo.get("created_at"),
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Gagal memperbarui judul conversation {conversation_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )