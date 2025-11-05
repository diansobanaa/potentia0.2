# File: backend/app/db/queries/conversation/message_list_queries.py

import logging
from uuid import UUID
from typing import List, Dict, Any, Tuple
from supabase import Client
from postgrest import APIResponse
from app.core.exceptions import DatabaseError

logger = logging.getLogger(__name__)

def get_conversation_messages_paginated(
    authed_client: Client,
    user_id: UUID,
    conversation_id: UUID,
    offset: int,
    limit: int
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Mengambil daftar pesan (user & assistant) untuk conversation_id tertentu.
    Dipesan dari yang terbaru (DESC) dan dipaginasi.
    
    Mengembalikan:
        Tuple berisi (list_of_messages, total_count).
    """
    try:
        # 1. Ambil data pesan yang dipaginasi
        # (ORDER BY created_at DESC - mengambil dari yang terakhir dibuat)
        list_response: APIResponse = authed_client.table("messages") \
            .select(
                "message_id",
                "role",
                "content",
                "created_at"
            ) \
            .eq("user_id", str(user_id)) \
            .eq("conversation_id", str(conversation_id)) \
            .order("created_at", desc=True) \
            .range(offset, offset + limit - 1) \
            .execute()

        # 2. Hitung total pesan dalam percakapan ini
        count_response: APIResponse = authed_client.table("messages") \
            .select("message_id", count="exact") \
            .eq("user_id", str(user_id)) \
            .eq("conversation_id", str(conversation_id)) \
            .execute()

        if list_response.data is None:
            logger.error(f"Supabase returned None data for messages query (convo_id: {conversation_id}).")
            raise DatabaseError("Gagal mengambil data pesan dari database.")
            
        messages = list_response.data
        total = count_response.count or 0

        logger.info(f"list message by conversation_id: {conversation_id}. Messages: {messages}")
        return messages, total

    except Exception as e:
        logger.error(f"Gagal mengambil data pesan paginasi untuk convo {conversation_id}: {e}", exc_info=True)
        raise DatabaseError(f"Error mengambil daftar pesan: {str(e)}")