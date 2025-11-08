# PARSE: 27-query-find-blocks.py
# (Diperbarui untuk AsyncClient native)

import logging
import asyncio
from typing import List, Dict, Any
from uuid import UUID
# --- PERBAIKAN: Impor AsyncClient ---
from supabase.client import AsyncClient
from app.core.exceptions import DatabaseError

logger = logging.getLogger(__name__)

async def find_relevant_blocks(
    authed_client: AsyncClient, # <-- Tipe diubah
    query_embedding: List[float],
    canvas_id: UUID
) -> List[Dict[str, Any]]:
    """
    (Async Native) Fungsi untuk memanggil RPC 'find_relevant_blocks'.
    """
    function_name = "find_relevant_blocks"
    try:
        params = {
            "query_embedding": query_embedding,
            "query_canvas_id": str(canvas_id)
        }
        # --- PERBAIKAN: Hapus 'to_thread', gunakan 'await' ---
        response = await authed_client.rpc(function_name, params).execute()
        
        if response.data:
            return response.data
        return []

    except Exception as e:
        logger.error(f"Error saat memanggil RPC {function_name} (async): {e}", exc_info=True)
        return []