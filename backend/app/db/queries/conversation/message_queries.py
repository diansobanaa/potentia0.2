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
# [MODIFIKASI] Tambahkan parameter token
# =======================================================================
async def add_message(
    authed_client: AsyncClient,
    user_id: UUID,
    conversation_id: UUID,
    context_id: Optional[UUID],
    role: Literal["user", "assistant", "system", "tool"],
    content: str,
    model_used: Optional[str] = None,
    # [BARU v3.2] Parameter untuk NFR Poin 8
    input_tokens: int = 0,
    output_tokens: int = 0
) -> Dict[str, Any]:
    """(Async Native) Menambahkan SATU pesan baru ke database."""
    try:
        payload = {
            "user_id": str(user_id),
            "conversation_id": str(conversation_id),
            "context_id": str(context_id) if context_id else None,
            "role": role,
            "content": content,
            "model_used": model_used,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens
        }
        
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
# [MODIFIKASI v3.2] Terima dan teruskan token count (Perbaikan Gap #1)
# =======================================================================
async def save_turn_messages(
    authed_client: AsyncClient,
    user_id: UUID,
    conversation_id: UUID,
    context_id: Optional[UUID],
    user_message_content: str,
    ai_message_content: str,
    # [BARU v3.2] Parameter untuk NFR Poin 8
    total_input_tokens: int = 0,
    total_output_tokens: int = 0
) -> Dict[str, Any]:
    """
    (Async Native) Menyimpan giliran percakapan (user dan AI).
    """
    try:
        # Pesan Pengguna
        user_message_db = await add_message(
            authed_client=authed_client,
            user_id=user_id,
            conversation_id=conversation_id,
            context_id=context_id,
            role="user",
            content=user_message_content,
            input_tokens=0,
            output_tokens=0
        )
        
        # Pesan Asisten (menyimpan SEMUA token count)
        await add_message(
            authed_client=authed_client,
            user_id=user_id,
            conversation_id=conversation_id,
            context_id=context_id,
            role="assistant",
            content=ai_message_content,
            input_tokens=total_input_tokens, # [PERBAIKAN]
            output_tokens=total_output_tokens # [PERBAIKAN]
        )

        if not user_message_db:
             raise DatabaseError("Pesan pengguna berhasil disimpan tetapi data tidak dikembalikan.")
             
        return user_message_db

    except Exception as e:
        logger.error(f"Error di save_turn_messages (async) untuk convo {conversation_id}: {e}", exc_info=True)
        raise DatabaseError(f"Error saving turn messages: {str(e)}")

# =======================================================================
# FUNGSI 3: Mengambil Pesan (Jalur Baca / "Read Path")
# [BARU v3.2] (Perbaikan Kekurangan #4)
# =======================================================================
async def get_all_conversation_messages(
    authed_client: AsyncClient,
    user_id: UUID,
    conversation_id: UUID,
    limit: int = 1000 # Ambil batas yang sangat tinggi untuk 'load_full_history'
) -> List[Dict[str, Any]]:
    """
    (Async Native) Mengambil SEMUA daftar pesan (user & assistant).
    Digunakan oleh 'load_full_history' (Goal 'chatgpt flow').
    """
    try:
        response = await authed_client.table("messages") \
            .select(
                "message_id",
                "role",
                "content",
                "created_at"
                # TODO: Ambil juga tool_calls jika disimpan sebagai JSON
            ) \
            .eq("user_id", str(user_id)) \
            .eq("conversation_id", str(conversation_id)) \
            .order("created_at", desc=False) \
            .limit(limit) \
            .execute()

        if response.data is None:
            raise DatabaseError("Gagal mengambil data pesan dari database.")
            
        return response.data

    except Exception as e:
        logger.error(f"Gagal mengambil semua data pesan (async) untuk convo {conversation_id}: {e}", exc_info=True)
        raise DatabaseError(f"Error mengambil daftar pesan: {str(e)}")

        
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