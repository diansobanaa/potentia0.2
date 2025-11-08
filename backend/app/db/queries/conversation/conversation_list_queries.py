# backend/app/db/queries/conversation/conversation_list_queries.py
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

async def get_user_conversations_paginated(
    authed_client: AsyncClient, # <-- Tipe diubah
    user_id: UUID,
    offset: int,
    limit: int
) -> Tuple[List[Dict[str, Any]], int]:
    """
    (Async Native) Mengambil daftar conversation dengan pagination.
    """
    try:
        # --- PERBAIKAN: Optimasi dengan asyncio.gather ---
        
        # 1. Ambil data pesan yang dipaginasi (Tugas 1)
        list_task = authed_client.table("conversations") \
            .select(
                "conversation_id",
                "title",
                "updated_at"
            ) \
            .eq("user_id", str(user_id)) \
            .order("updated_at", desc=True) \
            .range(offset, offset + limit - 1) \
            .execute()

        # 2. Hitung total pesan (Tugas 2)
        count_task = authed_client.table("conversations") \
            .select("conversation_id", count="exact") \
            .eq("user_id", str(user_id)) \
            .execute()
        
        # Jalankan paralel
        list_response, count_response = await asyncio.gather(
            list_task,
            count_task
        )
        # ---------------------------------------------

        if list_response.data is None:
            logger.error(f"Supabase returned None data for conversations query (user_id: {user_id}).")
            raise DatabaseError("Gagal mengambil data percakapan dari database.")
            
        conversations = list_response.data
        total = count_response.count or 0

        return conversations, total

    except Exception as e:
        logger.error(f"Gagal mengambil data percakapan paginasi (async) untuk user {user_id}: {e}", exc_info=True)
        raise DatabaseError(f"Error mengambil daftar percakapan: {str(e)}")