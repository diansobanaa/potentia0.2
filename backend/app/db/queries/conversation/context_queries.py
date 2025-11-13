# File: backend/app/db/queries/conversation/context_queries.py
# (Diperbarui v3.2 - Perbaikan Gap #7: 'chatgpt flow')

import logging
from uuid import UUID
from typing import Optional, Dict, Any, List
from supabase.client import AsyncClient
from postgrest import APIResponse
from postgrest.exceptions import APIError
from app.core.exceptions import DatabaseError

logger = logging.getLogger(__name__)

# --- [FUNGSI USANG v1] ---
# Kita biarkan agar tidak merusak impor lain, tapi v3.2 tidak menggunakannya
async def create_context(*args, **kwargs):
    logger.warning("Fungsi 'create_context' usang dan tidak boleh dipanggil.")
    pass

async def get_active_context_by_user(*args, **kwargs):
    logger.warning("Fungsi 'get_active_context_by_user' usang.")
    return None

async def get_context_with_summary_by_id(*args, **kwargs):
    logger.warning("Fungsi 'get_context_with_summary_by_id' usang.")
    return None

async def get_context_by_summary_id(*args, **kwargs):
    logger.warning("Fungsi 'get_context_by_summary_id' usang.")
    return None
# --- AKHIR FUNGSI USANG ---


# [PERBAIKAN v3.2] Menggantikan 'create_summary_for_context' (Perbaikan Kekurangan #2)
async def create_summary_for_conversation(
    authed_client: AsyncClient,
    user_id: UUID,
    conversation_id: UUID, # [UBAH v3.0] Gunakan conversation_id
    summary_text: str
) -> Dict[str, Any]:
    """
    (Async Native) [v3.0] Membuat baris 'summary_memory' baru.
    (Perbaikan Gap #7 - 'chatgpt flow')
    """
    try:
        payload = {
            "user_id": str(user_id),
            "conversation_id": str(conversation_id), # [UBAH v3.0]
            "summary_text": summary_text
        }
        response: APIResponse = await authed_client.table("summary_memory") \
            .insert(payload, returning="representation") \
            .execute()
        
        if not response.data:
            raise DatabaseError("Gagal membuat baris 'summary_memory'.")
        
        return response.data[0]
        
    except Exception as e:
        logger.error(f"Error creating new summary (async v3.0): {e}", exc_info=True)
        raise DatabaseError(f"Error creating new summary: {str(e)}")
    
        
async def find_relevant_summaries(
    authed_client: AsyncClient,
    user_id: UUID,
    query_embedding: List[float],
    ts_query: str, # [UBAH v3.0] Tambahkan ts_query
    match_threshold: float = 0.5,
    match_count: int = 10
) -> List[Dict[str, Any]]:
    """
    (Async Native) [v3.0] Memanggil RPC 'find_relevant_summaries'.
    """
    try:
        params = {
            "p_user_id": str(user_id),
            "p_query_embedding": query_embedding,
            "p_query_text": ts_query, # [UBAH v3.0]
            "p_match_threshold": match_threshold,
            "p_match_count": match_count
        }
        response: APIResponse = await authed_client.rpc('find_relevant_summaries', params).execute()
        return response.data if response.data else []
    except Exception as e:
        logger.error(f"Gagal memanggil RPC 'find_relevant_summaries': {e}", exc_info=True)
        return []