# File: backend/app/db/queries/conversation/message_queries.py
# (Versi ini memiliki indentasi yang 100% benar)

import logging
import asyncio # Diperlukan untuk perbaikan 'to_thread'
from uuid import UUID
from typing import List, Dict, Any, Literal, Optional
from supabase import Client
from postgrest import APIResponse
from app.core.exceptions import DatabaseError
from postgrest.exceptions import APIError

logger = logging.getLogger(__name__)

# =======================================================================
# FUNGSI 1: Menambahkan Satu Pesan (Helper)
# =======================================================================
def add_message(
    authed_client: Client,
    user_id: UUID,
    conversation_id: UUID,
    context_id: Optional[UUID], # Dibuat opsional agar lebih tangguh
    role: Literal["user", "assistant", "system", "tool"],
    content: str,
    model_used: Optional[str] = None
) -> Dict[str, Any]:
    """Menambahkan SATU pesan baru ke database."""
    try:
        payload = {
            "user_id": str(user_id),
            "conversation_id": str(conversation_id),
            "context_id": str(context_id) if context_id else None,
            "role": role,
            "content": content,
            "model_used": model_used
        }
        
        # Blok ini harus memiliki indentasi yang konsisten
        response: APIResponse = authed_client.table("messages") \
            .insert(payload, returning="representation") \
            .execute()

        if not response.data:
            raise DatabaseError("Gagal menambahkan pesan, tidak ada data yang dikembalikan.")
            
        return response.data[0]

    except Exception as e:
        logger.error(f"Error adding single message: {e}", exc_info=True)
        raise DatabaseError(f"Error adding message: {str(e)}")


# =======================================================================
# FUNGSI 2: Menyimpan Giliran (Jalur Tulis / "Write Path")
# =======================================================================
def save_turn_messages(
    authed_client: Client,
    user_id: UUID,
    conversation_id: UUID,
    context_id: Optional[UUID],
    user_message_content: str,
    ai_message_content: str
) -> Dict[str, Any]:
    """
    Menyimpan giliran percakapan (user dan AI) sebagai dua entri terpisah
    untuk menjamin integritas 'created_at' dan urutan kronologis.
    """
    
    user_message_db = None
    try:
        # 1. Simpan Pesan Pengguna (Pertama)
        logger.debug(f"Menyimpan pesan PENGGUNA untuk convo {conversation_id}...")
        user_message_db = add_message(
            authed_client=authed_client,
            user_id=user_id,
            conversation_id=conversation_id,
            context_id=context_id,
            role="user",
            content=user_message_content
        )
        
        # 2. Simpan Pesan Asisten (Kedua)
        logger.debug(f"Menyimpan pesan ASISTEN untuk convo {conversation_id}...")
        ai_message_db = add_message(
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
        logger.error(f"Error di save_turn_messages untuk convo {conversation_id}: {e}", exc_info=True)
        raise DatabaseError(f"Error saving turn messages: {str(e)}")


# =======================================================================
# FUNGSI 3: Mengambil Pesan (Jalur Baca / "Read Path")
# =======================================================================

def get_messages_by_context_id(
    authed_client: Client,
    context_id: UUID,
    limit: int = 15
) -> List[Dict[str, Any]]:
    """
    Mengambil riwayat pesan terbaru untuk context_id tertentu.
    Ini dipanggil oleh ContextManager untuk 'load_memory_for_judge'.
    
    PENTING: Ini adalah fungsi SINKRON (sync) karena dipanggil
    oleh ContextManager di dalam 'asyncio.to_thread'.
    """
    try:
        logger.debug(f"Mengambil {limit} pesan terakhir untuk context_id {context_id}...")
        
        response: APIResponse = authed_client.table("messages") \
            .select("role, content, created_at") \
            .eq("context_id", str(context_id)) \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()

        if not response.data and isinstance(response.data, list):
            logger.warning(f"Tidak ada riwayat pesan ditemukan untuk context_id {context_id}")
            return []
        
        # Kembalikan dalam urutan kronologis (ASC) agar LLM bisa membacanya
        return sorted(response.data, key=lambda x: x['created_at'])

    except Exception as e:
        logger.error(f"Gagal mengambil pesan untuk context {context_id}: {e}", exc_info=True)
        raise DatabaseError(f"Error retrieving messages: {str(e)}")