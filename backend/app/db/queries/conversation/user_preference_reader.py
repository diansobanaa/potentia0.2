# File: backend/app/db/queries/conversation/user_preference_reader.py

import logging
import asyncio
from uuid import UUID
from typing import List, Dict, Any, Optional
from supabase import Client as SupabaseClient
from app.core.exceptions import DatabaseError
from postgrest.exceptions import APIError

logger = logging.getLogger(__name__)

# Batas (limit) keamanan untuk kueri
MAX_FACTS_LIMIT = 20
MAX_MEMORIES_LIMIT = 5

async def get_user_facts_and_rules(
    authed_client: SupabaseClient,
    user_id: UUID
) -> List[Dict[str, Any]]:
    """
    Mengambil "Fakta & Aturan" (data terstruktur) dari tabel SQL 'user_preferences'.
    Ini adalah data yang harus *selalu* diterapkan (misal: Profil, Larangan).
    
    Tipe yang diambil: PROFIL_PENGGUNA, GAYA_BAHASA, FORMAT, LARANGAN
    """
    try:
        logger.info(f"Mengambil Fakta & Aturan (SQL) untuk user {user_id}...")
        
        # Tipe data terstruktur yang ingin kita ambil
        fact_types = [
            "PROFIL_PENGGUNA", 
            "GAYA_BAHASA", 
            "FORMAT", 
            "LARANGAN"
        ]

        # Definisikan panggilan sinkron (blocking)
        def sync_db_call():
            # Kueri ini menggunakan indeks 'idx_user_preferences_main_query'
            # (user_id, active, type, priority)
            response = authed_client.table("user_preferences").select(
                "type, description, priority"
            ).eq(
                "user_id", str(user_id)
            ).eq(
                "active", True
            ).in_(
                "type", fact_types
            ).order(
                "priority", desc=True
            ).order(
                "created_at", desc=True # Ambil yang terbaru jika prioritas sama
            ).limit(
                MAX_FACTS_LIMIT
            ).execute()
            
            if not response.data and isinstance(response.data, list):
                return []
            return response.data

        # Jalankan di thread terpisah untuk menghindari pemblokiran
        data = await asyncio.to_thread(sync_db_call)
        logger.info(f"Berhasil mengambil {len(data)} Fakta & Aturan (SQL) untuk user {user_id}.")
        return data

    except APIError as e:
        logger.error(f"APIError saat mengambil Fakta & Aturan (SQL) untuk user {user_id}: {e.message}", exc_info=True)
        return [] # Jangan gagalkan seluruh request jika memori gagal
    except Exception as e:
        logger.error(f"Error saat mengambil Fakta & Aturan (SQL) untuk user {user_id}: {e}", exc_info=True)
        return []


async def get_user_semantic_memories(
    authed_client: SupabaseClient,
    user_id: UUID,
    query_embedding: List[float],
    match_threshold: float = 0.5, # Hanya ambil memori yang 'cukup' relevan
    match_count: int = MAX_MEMORIES_LIMIT
) -> List[Dict[str, Any]]:
    """
    Mengambil "Memori & Konteks" (data semantik) dari tabel Vektor
    'user_semantic_memories' menggunakan pencarian kemiripan.
    
    Tipe yang diambil: MEMORI, TUJUAN_PENGGUNA, TOPIK
    """
    try:
        # Jika embedding gagal (list kosong), jangan panggil RPC.
        if not query_embedding:
            logger.warning(f"Melewatkan pencarian Memori Semantik karena query_embedding kosong.")
            return []

        logger.info(f"Mengambil Memori Semantik (Vektor) untuk user {user_id}...")
        
        # Definisikan panggilan sinkron (blocking)
        def sync_db_call():
            response = authed_client.rpc(
                'match_user_semantic_memories',
                {
                    'p_user_id': str(user_id),
                    'query_embedding': query_embedding,
                    'match_threshold': match_threshold,
                    'match_count': match_count
                }
            ).execute()

            if not response.data or not isinstance(response.data, list):
                return []
            return response.data

        data = await asyncio.to_thread(sync_db_call)
        logger.info(f"Berhasil mengambil {len(data)} memori semantik (vektor) untuk user {user_id}.")
        return data

    except APIError as e:
        # Tangani jika RPC belum dibuat (404 Not Found)
        if "PGRST202" in str(e.message): # 'Could not find the function'
             logger.error(
                 f"FATAL: Fungsi RPC 'match_user_semantic_memories' "
                 f"tidak ditemukan di database Anda. Silakan jalankan file SQL "
                 f"create_rpc_match_memories.sql. Error: {e.message}"
             )
        else:
             logger.error(f"APIError saat mengambil Memori Semantik (Vektor) untuk user {user_id}: {e.message}", exc_info=True)
        return [] # Jangan gagalkan seluruh request
    except Exception as e:
        logger.error(f"Error saat mengambil Memori Semantik (Vektor) untuk user {user_id}: {e}", exc_info=True)
        return []