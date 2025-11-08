# File: backend/app/db/queries/conversation/user_preference_reader.py
# (Diperbarui untuk AsyncClient native)

import logging
import asyncio
from uuid import UUID
from typing import List, Dict, Any, Optional
# --- PERBAIKAN: Impor AsyncClient ---
from supabase.client import AsyncClient
from app.core.exceptions import DatabaseError
from postgrest.exceptions import APIError

logger = logging.getLogger(__name__)

MAX_FACTS_LIMIT = 20
MAX_MEMORIES_LIMIT = 5

async def get_user_facts_and_rules(
    authed_client: AsyncClient, # <-- Tipe diubah
    user_id: UUID
) -> List[Dict[str, Any]]:
    """
    (Async Native) Mengambil "Fakta & Aturan" (data SQL).
    """
    try:
        logger.info(f"Mengambil Fakta & Aturan (SQL) untuk user {user_id}...")
        
        fact_types = ["PROFIL_PENGGUNA", "GAYA_BAHASA", "FORMAT", "LARANGAN"]

        # --- PERBAIKAN: Hapus 'to_thread' / 'sync_db_call', gunakan 'await' ---
        response = await authed_client.table("user_preferences").select(
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
            "created_at", desc=True
        ).limit(
            MAX_FACTS_LIMIT
        ).execute()
        
        data = response.data
        if not data and isinstance(data, list):
            return []
        # ---------------------------------------------

        logger.info(f"Berhasil mengambil {len(data)} Fakta & Aturan (SQL) untuk user {user_id}.")
        return data

    except APIError as e:
        logger.error(f"APIError saat mengambil Fakta & Aturan (async) {user_id}: {e.message}", exc_info=True)
        return []
    except Exception as e:
        logger.error(f"Error saat mengambil Fakta & Aturan (async) {user_id}: {e}", exc_info=True)
        return []

async def get_user_semantic_memories(
    authed_client: AsyncClient, # <-- Tipe diubah
    user_id: UUID,
    query_embedding: List[float],
    match_threshold: float = 0.5,
    match_count: int = MAX_MEMORIES_LIMIT
) -> List[Dict[str, Any]]:
    """
    (Async Native) Mengambil "Memori & Konteks" (Vektor) via RPC.
    """
    try:
        if not query_embedding:
            logger.warning(f"Melewatkan pencarian Memori Semantik karena query_embedding kosong.")
            return []

        logger.info(f"Mengambil Memori Semantik (Vektor) untuk user {user_id}...")
        
        # --- PERBAIKAN: Hapus 'to_thread' / 'sync_db_call', gunakan 'await' ---
        response = await authed_client.rpc(
            'match_user_semantic_memories',
            {
                'p_user_id': str(user_id),
                'query_embedding': query_embedding,
                'match_threshold': match_threshold,
                'match_count': match_count
            }
        ).execute()

        data = response.data
        if not data or not isinstance(data, list):
            return []
        # ---------------------------------------------
        
        logger.info(f"Berhasil mengambil {len(data)} memori semantik (vektor) untuk user {user_id}.")
        return data

    except APIError as e:
        if "PGRST202" in str(e.message):
             logger.error(f"FATAL: Fungsi RPC 'match_user_semantic_memories' tidak ditemukan.")
        else:
             logger.error(f"APIError saat mengambil Memori Semantik (async) {user_id}: {e.message}", exc_info=True)
        return []
    except Exception as e:
        logger.error(f"Error saat mengambil Memori Semantik (async) {user_id}: {e}", exc_info=True)
        return []