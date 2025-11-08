# File: backend/app/db/queries/conversation/message_list_queries.py
# (Diperbarui untuk AsyncClient native dan asyncio.gather)

import logging
from uuid import UUID
from typing import List, Dict, Any, Tuple
# --- PERBAIKAN: Impor AsyncClient ---
from supabase.client import AsyncClient
from postgrest import APIResponse
from app.core.exceptions import DatabaseError
import asyncio # <-- [DITAMBAHKAN]

logger = logging.getLogger(__name__)

async def get_conversation_messages_paginated(
    authed_client: AsyncClient, # <-- Tipe diubah
    user_id: UUID,
    conversation_id: UUID,
    offset: int,
    limit: int
) -> Tuple[List[Dict[str, Any]], int]:
    """
    (Async Native) Mengambil daftar pesan (user & assistant) dengan pagination.
    """
    try:
        # --- PERBAIKAN: Optimasi dengan asyncio.gather ---
        
        # 1. Ambil data pesan yang dipaginasi (Tugas 1)
        list_task = authed_client.table("messages") \
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

        # 2. Hitung total pesan (Tugas 2)
        count_task = authed_client.table("messages") \
            .select("message_id", count="exact") \
            .eq("user_id", str(user_id)) \
            .eq("conversation_id", str(conversation_id)) \
            .execute()
        
        # Jalankan paralel
        list_response, count_response = await asyncio.gather(
            list_task,
            count_task
        )
        # ---------------------------------------------

        if list_response.data is None:
            logger.error(f"Supabase returned None data for messages query (convo_id: {conversation_id}).")
            raise DatabaseError("Gagal mengambil data pesan dari database.")
            
        messages = list_response.data
        total = count_response.count or 0

        logger.info(f"list message by conversation_id: {conversation_id}. Messages: {messages}")
        return messages, total

    except Exception as e:
        logger.error(f"Gagal mengambil data pesan paginasi (async) untuk convo {conversation_id}: {e}", exc_info=True)
        raise DatabaseError(f"Error mengambil daftar pesan: {str(e)}")