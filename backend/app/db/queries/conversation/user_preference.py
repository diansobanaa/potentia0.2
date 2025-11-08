# File: app/db/queries/conversation/user_preference.py
# (Diperbarui dengan perbaikan 'insert' syntax)

import logging
import asyncio
from uuid import UUID
from typing import List, Dict, Any
from supabase.client import AsyncClient
from postgrest import APIResponse
from app.core.exceptions import DatabaseError
from postgrest.exceptions import APIError

logger = logging.getLogger(__name__)

async def execute_batch_inserts(
    authed_client: AsyncClient,
    user_id: UUID,
    sql_batch: List[Dict[str, Any]],
    vector_batch: List[Dict[str, Any]]
):
    """
    (Async Native) Mengeksekusi batch insert ke tabel preferensi.
    """
    try:
        if not sql_batch and not vector_batch:
            return

        if sql_batch:
            logger.info(f"Menjalankan SQL batch insert (async) untuk {len(sql_batch)} item preferensi...")
            
            # --- PERBAIKAN: Tambahkan returning="representation" ---
            sql_response: APIResponse = await authed_client.table("user_preferences") \
                .insert(sql_batch, returning="representation") \
                .execute()
            # --------------------------------------------------
            
            if not sql_response.data and len(sql_batch) > 0:
                logger.warning("SQL batch insert 'user_preferences' tidak mengembalikan data.")
            else:
                logger.info(f"Berhasil menyimpan {len(sql_response.data)} item ke 'user_preferences'.")

        if vector_batch:
            logger.info(f"Menjalankan Vektor batch insert (async) untuk {len(vector_batch)} item memori...")

            # --- PERBAIKAN: Tambahkan returning="representation" ---
            vector_response: APIResponse = await authed_client.table("user_semantic_memories") \
                .insert(vector_batch, returning="representation") \
                .execute()
            # --------------------------------------------------
                
            if not vector_response.data and len(vector_batch) > 0:
                 logger.warning("Vektor batch insert 'user_semantic_memories' tidak mengembalikan data.")
            else:
                logger.info(f"Berhasil menyimpan {len(vector_response.data)} item ke 'user_semantic_memories'.")
    
    except APIError as e:
        logger.error(f"APIError saat batch insert preferensi (async) untuk user {user_id}: {e.message}", exc_info=True)
        raise DatabaseError(f"APIError: {e.message}")
    except Exception as e:
        logger.error(f"Error saat batch insert preferensi (async) untuk user {user_id}: {e}", exc_info=True)
        raise DatabaseError(f"Error: {str(e)}")