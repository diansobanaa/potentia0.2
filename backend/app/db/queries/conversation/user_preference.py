# File: app/db/queries/conversation/user_preference.py

import logging
import asyncio  # <-- 1. Impor asyncio
from uuid import UUID
from typing import List, Dict, Any
from supabase import Client
from postgrest import APIResponse
from app.core.exceptions import DatabaseError
from postgrest.exceptions import APIError

logger = logging.getLogger(__name__)

async def execute_batch_inserts(
    authed_client: Client,
    user_id: UUID,
    sql_batch: List[Dict[str, Any]],
    vector_batch: List[Dict[str, Any]]
):
    """
    Mengeksekusi batch insert ke tabel user_preferences (SQL)
    dan user_semantic_memories (Vektor) secara asinkron.
    """
    
    # PENTING: Fungsi ini MENGHARAPKAN data (UUIDs) sudah
    # dikonversi menjadi string di dalam batch oleh 'user_preference_memory_service'.
    
    try:
        if not sql_batch and not vector_batch:
            logger.info("Tidak ada batch data untuk dieksekusi.")
            return

        # --- AWAL PERBAIKAN (Async/Sync Mismatch) ---
        
        if sql_batch:
            logger.info(f"Menjalankan SQL batch insert untuk {len(sql_batch)} item preferensi...")
            
            # 2. Definisikan fungsi sinkron (blocking)
            def sync_sql_insert():
                return authed_client.table("user_preferences") \
                    .insert(sql_batch) \
                    .execute()

            # 3. Jalankan fungsi blocking di thread terpisah dan 'await'
            sql_response: APIResponse = await asyncio.to_thread(sync_sql_insert)
            
            if not sql_response.data and len(sql_batch) > 0:
                logger.warning("SQL batch insert 'user_preferences' tidak mengembalikan data.")
            else:
                logger.info(f"Berhasil menyimpan {len(sql_response.data)} item ke 'user_preferences'.")

        if vector_batch:
            logger.info(f"Menjalankan Vektor batch insert untuk {len(vector_batch)} item memori...")

            # 2. Definisikan fungsi sinkron (blocking)
            def sync_vector_insert():
                return authed_client.table("user_semantic_memories") \
                    .insert(vector_batch) \
                    .execute()
            
            # 3. Jalankan fungsi blocking di thread terpisah dan 'await'
            vector_response: APIResponse = await asyncio.to_thread(sync_vector_insert)
                
            if not vector_response.data and len(vector_batch) > 0:
                 logger.warning("Vektor batch insert 'user_semantic_memories' tidak mengembalikan data.")
            else:
                logger.info(f"Berhasil menyimpan {len(vector_response.data)} item ke 'user_semantic_memories'.")

        # --- AKHIR PERBAIKAN ---
    
    except APIError as e:
        logger.error(f"APIError saat batch insert preferensi untuk user {user_id}: {e.message}", exc_info=True)
        # Melempar ulang error agar service bisa menangkapnya
        raise DatabaseError(f"APIError: {e.message}")
    except Exception as e:
        logger.error(f"Error saat batch insert preferensi untuk user {user_id}: {e}", exc_info=True)
        # Melempar ulang error agar service bisa menangkapnya
        raise DatabaseError(f"Error: {str(e)}")
