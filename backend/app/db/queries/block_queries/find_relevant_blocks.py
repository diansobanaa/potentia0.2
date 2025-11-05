# PARSE: 27-query-find-blocks.py

import logging
import asyncio
from typing import List, Dict, Any
from uuid import UUID
from supabase import Client as SupabaseClient
from app.core.exceptions import DatabaseError

logger = logging.getLogger(__name__)

def find_relevant_blocks(
    authed_client: SupabaseClient, 
    query_embedding: List[float],
    canvas_id: UUID
) -> List[Dict[str, Any]]:
    """
    Fungsi SINKRON (blocking) untuk memanggil RPC 'find_relevant_blocks'.
    Ini akan dibungkus oleh 'asyncio.to_thread' oleh service.
    """
    function_name = "find_relevant_blocks"
    try:
        params = {
            "query_embedding": query_embedding,
            "query_canvas_id": str(canvas_id)
        }
        # Panggil .execute() secara sinkron
        response = authed_client.rpc(function_name, params).execute()
        
        if response.data:
            return response.data
        return []

    except Exception as e:
        logger.error(f"Error saat memanggil RPC {function_name}: {e}", exc_info=True)
        # Jangan lempar error, kembalikan list kosong agar tool bisa 
        # melaporkan "tidak ada" daripada crash.
        return []