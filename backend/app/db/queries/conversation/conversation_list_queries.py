#backend\app\db\queries\conversation\conversation_list_queries.py
import logging
from uuid import UUID
from typing import List, Dict, Any, Tuple
from supabase import Client
from postgrest import APIResponse
from app.core.exceptions import DatabaseError

logger = logging.getLogger(__name__)

def get_user_conversations_paginated(
    authed_client: Client,
    user_id: UUID,
    offset: int,
    limit: int
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Mengambil daftar conversation untuk user tertentu dengan pagination dan total count.
    Menggunakan Supabase client.

    Returns:
        Tuple berisi (list_of_conversations, total_count).
    """
    try:
        # Query untuk mengambil data conversation yang dipaginasi
        # Supabase menggunakan .range() untuk offset/limit. Range bersifat inklusif.
        # Misal: offset=0, limit=20 -> range(0, 19)
        list_response: APIResponse = authed_client.table("conversations") \
            .select(
                "conversation_id",
                "title",
                "updated_at"
            ) \
            .eq("user_id", str(user_id)) \
            .order("updated_at", desc=True) \
            .range(offset, offset + limit - 1) \
            .execute()

        # Query untuk menghitung total keseluruhan conversation
        # Menggunakan count="exact" adalah cara efisien di Supabase
        count_response: APIResponse = authed_client.table("conversations") \
            .select("conversation_id", count="exact") \
            .eq("user_id", str(user_id)) \
            .execute()

        if list_response.data is None:
            # Handle kasus di mana Supabase mengembalikan error tanpa memunculkan exception
            logger.error(f"Supabase returned None data for user {user_id} list query.")
            raise DatabaseError("Gagal mengambil data conversation dari database.")
            
        conversations = list_response.data
        total = count_response.count or 0 # count bisa None jika tidak ada data

        return conversations, total

    except Exception as e:
        logger.error(f"Gagal mengambil data conversation paginasi untuk user {user_id}: {e}", exc_info=True)
        raise DatabaseError(f"Error mengambil daftar conversation: {str(e)}")