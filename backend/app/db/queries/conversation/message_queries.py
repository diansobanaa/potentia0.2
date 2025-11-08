# File: backend/app/db/queries/conversation/message_queries.py
# (Diperbarui untuk AsyncClient native dan asyncio.gather)

import logging
import asyncio
from uuid import UUID
from typing import List, Dict, Any, Literal, Optional, Tuple
# --- PERBAIKAN: Impor AsyncClient ---
from supabase.client import AsyncClient
from postgrest import APIResponse
from app.core.exceptions import DatabaseError
from postgrest.exceptions import APIError

logger = logging.getLogger(__name__)

# =======================================================================
# FUNGSI 1: Menambahkan Satu Pesan (Helper Async)
# =======================================================================
async def add_message(
    authed_client: AsyncClient, # <-- Tipe diubah
    user_id: UUID,
    conversation_id: UUID,
    context_id: Optional[UUID],
    role: Literal["user", "assistant", "system", "tool"],
    content: str,
    model_used: Optional[str] = None
) -> Dict[str, Any]:
    """(Async Native) Menambahkan SATU pesan baru ke database."""
    try:
        payload = {
            "user_id": str(user_id),
            "conversation_id": str(conversation_id),
            "context_id": str(context_id) if context_id else None,
            "role": role,
            "content": content,
            "model_used": model_used
        }
        
        # --- PERBAIKAN: Gunakan 'await' ---
        response: APIResponse = await authed_client.table("messages") \
            .insert(payload, returning="representation") \
            .execute()

        if not response.data:
            raise DatabaseError("Gagal menambahkan pesan, tidak ada data yang dikembalikan.")
            
        return response.data[0]

    except Exception as e:
        logger.error(f"Error adding single message (async): {e}", exc_info=True)
        raise DatabaseError(f"Error adding message: {str(e)}")

# =======================================================================
# FUNGSI 2: Menyimpan Giliran (Jalur Tulis / "Write Path")
# =======================================================================
async def save_turn_messages(
    authed_client: AsyncClient, # <-- Tipe diubah
    user_id: UUID,
    conversation_id: UUID,
    context_id: Optional[UUID],
    user_message_content: str,
    ai_message_content: str
) -> Dict[str, Any]:
    """
    (Async Native) Menyimpan giliran percakapan (user dan AI).
    """
    try:
        # --- PERBAIKAN: Panggil helper async ---
        logger.debug(f"Menyimpan pesan PENGGUNA (async) untuk convo {conversation_id}...")
        user_message_db = await add_message(
            authed_client=authed_client,
            user_id=user_id,
            conversation_id=conversation_id,
            context_id=context_id,
            role="user",
            content=user_message_content
        )
        
        logger.debug(f"Menyimpan pesan ASISTEN (async) untuk convo {conversation_id}...")
        await add_message(
            authed_client=authed_client,
            user_id=user_id,
            conversation_id=conversation_id,
            context_id=context_id,
            role="assistant",
            content=ai_message_content
        )

        if not user_message_db:
             raise DatabaseError("Pesan pengguna berhasil disimpan tetapi data tidak dikembalikan.")
             
        return user_message_db

    except Exception as e:
        logger.error(f"Error di save_turn_messages (async) untuk convo {conversation_id}: {e}", exc_info=True)
        raise DatabaseError(f"Error saving turn messages: {str(e)}")

# =======================================================================
# FUNGSI 3: Mengambil Pesan (Jalur Baca / "Read Path")
# =======================================================================

async def get_messages_by_context_id(
    authed_client: AsyncClient, # <-- Tipe diubah
    context_id: UUID,
    limit: int = 15
) -> List[Dict[str, Any]]:
    """
    (Async Native) Mengambil riwayat pesan terbaru untuk context_id.
    """
    try:
        logger.debug(f"Mengambil {limit} pesan terakhir untuk context_id {context_id}...")
        
        # --- PERBAIKAN: Gunakan 'await' ---
        response: APIResponse = await authed_client.table("messages") \
            .select("role, content, created_at") \
            .eq("context_id", str(context_id)) \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()

        if not response.data and isinstance(response.data, list):
            logger.warning(f"Tidak ada riwayat pesan ditemukan untuk context_id {context_id}")
            return []
        
        return sorted(response.data, key=lambda x: x['created_at'])

    except Exception as e:
        logger.error(f"Gagal mengambil pesan (async) untuk context {context_id}: {e}", exc_info=True)
        raise DatabaseError(f"Error retrieving messages: {str(e)}")
    
async def get_first_turn_messages(
    authed_client: AsyncClient, # <-- Tipe diubah
    user_id: UUID,
    conversation_id: UUID
) -> Tuple[Optional[str], Optional[str]]:
    """
    (Async Native) Mengambil pesan 'user' pertama dan 'assistant' pertama.
    """
    try:
        # --- PERBAIKAN: Optimasi dengan asyncio.gather ---
        user_task = authed_client.table("messages") \
            .select("content") \
            .eq("user_id", str(user_id)) \
            .eq("conversation_id", str(conversation_id)) \
            .eq("role", "user") \
            .order("created_at", desc=False) \
            .limit(1) \
            .maybe_single() \
            .execute()
        
        ai_task = authed_client.table("messages") \
            .select("content") \
            .eq("user_id", str(user_id)) \
            .eq("conversation_id", str(conversation_id)) \
            .eq("role", "assistant") \
            .order("created_at", desc=False) \
            .limit(1) \
            .maybe_single() \
            .execute()
        
        user_response, ai_response = await asyncio.gather(user_task, ai_task)
        # ---------------------------------------------
        
        user_msg = user_response.data.get("content") if user_response and user_response.data else None
        ai_msg = ai_response.data.get("content") if ai_response and ai_response.data else None

        return user_msg, ai_msg

    except Exception as e:
        logger.error(f"Gagal mengambil pesan pertama (async) untuk convo {conversation_id}: {e}", exc_info=True)
        return None, None