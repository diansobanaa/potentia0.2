# backend/app/db/queries/conversation/context_queries.py
# (Diperbarui untuk AsyncClient native)

import logging
from uuid import UUID
from typing import Optional, Dict, Any, List
# --- PERBAIKAN: Impor AsyncClient ---
from supabase.client import AsyncClient
from postgrest import APIResponse
from postgrest.exceptions import APIError
from app.core.exceptions import DatabaseError

logger = logging.getLogger(__name__)

async def create_context(
    authed_client: AsyncClient, 
    user_id: UUID, 
    conversation_id: UUID,
    label: str = 'user',
    status: str = 'active'
) -> Dict[str, Any]:
    """
    (Async Native) Hanya membuat satu baris 'context' baru.
    """
    try:
        payload = {
            "user_id": str(user_id),
            "conversation_id": str(conversation_id),
            "label": label,
            "status": status
        }
        # --- PERBAIKAN: Tambahkan returning="representation" ---
        response: APIResponse = await authed_client.table("context") \
            .insert(payload, returning="representation") \
            .execute()
        # --------------------------------------------------
            
        if not response.data:
            raise DatabaseError("Gagal membuat baris 'context', tidak ada data yang dikembalikan.")
            
        return response.data[0]
        
    except Exception as e:
        logger.error(f"Error creating new context (async): {e}", exc_info=True)
        raise DatabaseError(f"Error creating new context: {str(e)}")
    
async def create_summary_for_context(
    authed_client: AsyncClient,
    user_id: UUID,
    context_id: UUID,
    summary_text: str
) -> Dict[str, Any]:
    """
    (Async Native) Hanya membuat satu baris 'summary_memory' baru.
    """
    try:
        payload = {
            "user_id": str(user_id),
            "context_id": str(context_id),
            "summary_text": summary_text
        }
        # --- PERBAIKAN: Tambahkan returning="representation" ---
        response: APIResponse = await authed_client.table("summary_memory") \
            .insert(payload, returning="representation") \
            .execute()
        # --------------------------------------------------
        
        if not response.data:
            raise DatabaseError("Gagal membuat baris 'summary_memory'.")
        
        return response.data[0]
        
    except Exception as e:
        logger.error(f"Error creating new summary (async): {e}", exc_info=True)
        raise DatabaseError(f"Error creating new summary: {str(e)}")
    
async def get_active_context_by_user(
    authed_client: AsyncClient, # <-- Tipe diubah
    user_id: UUID,
    conversation_id: UUID
) -> Optional[Dict[str, Any]]:
    """
    (Async Native) Mengambil konteks aktif.
    """
    try:
        # --- PERBAIKAN: Gunakan 'await' ---
        response: APIResponse = await (
            authed_client.table("context")
            .select("*, summary:summary_memory(*)") 
            .eq("user_id", str(user_id))
            .eq("conversation_id", str(conversation_id))
            .eq("status", "active") 
            .order("created_at", desc=True)
            .limit(1)
            .maybe_single()
            .execute()
        )
        return response.data if response and response.data else None
    except APIError as e:
        if e.code == '204' or "Missing response" in e.message: 
            return None 
        raise DatabaseError(f"Error getting active context: {e.message}")
    except Exception as e:
        raise DatabaseError(f"Error getting active context: {str(e)}")

async def get_context_with_summary_by_id(
    authed_client: AsyncClient, # <-- Tipe diubah
    context_id: UUID
) -> Optional[Dict[str, Any]]:
    """
    (Async Native) Mengambil konteks by ID.
    """
    try:
        # --- PERBAIKAN: Gunakan 'await' ---
        response: APIResponse = await authed_client.table("context") \
            .select("*, summary:summary_memory(*)") \
            .eq("context_id", str(context_id)) \
            .single() \
            .execute()
        return response.data
    except APIError as e:
        if e.code == '204' or "Missing response" in e.message: 
            return None 
        raise DatabaseError(f"Error getting context by id: {e.message}")
    except Exception as e:
        raise DatabaseError(f"Error getting context by id: {str(e)}")

async def get_context_by_summary_id(
    authed_client: AsyncClient, # <-- Tipe diubah
    summary_id: UUID
) -> Optional[Dict[str, Any]]:
    """
    (Async Native) Mengambil konteks by Summary ID.
    """
    try:
        # --- PERBAIKAN: Gunakan 'await' ---
        response: APIResponse = await (
            authed_client.table("summary_memory")
            .select("*, context(*, summary:summary_memory(*))")
            .eq("summary_id", str(summary_id))
            .limit(1)
            .limit(1, foreign_table="context")
            .limit(1, foreign_table="summary_memory")
            .maybe_single()
            .execute()
        )
        if response and response.data:
            return response.data.get("context") 
        return None
    except APIError as e:
        if e.code == '204' or "Missing response" in e.message: 
            return None 
        raise DatabaseError(f"Error getting context by summary_id: {e.message}")
    except Exception as e:
        raise DatabaseError(f"Error getting context by summary_id: {str(e)}")
        
async def find_relevant_summaries(
    authed_client: AsyncClient, # <-- Tipe diubah
    user_id: UUID,
    query_embedding: List[float],
    match_threshold: float = 0.7,
    match_count: int = 5
) -> List[Dict[str, Any]]:
    """
    (Async Native) Memanggil RPC 'find_relevant_summaries'.
    """
    try:
        params = {
            "p_user_id": str(user_id),
            "p_query_embedding": query_embedding,
            "p_match_threshold": match_threshold,
            "p_match_count": match_count
        }
        # --- PERBAIKAN: Gunakan 'await' ---
        response: APIResponse = await authed_client.rpc('find_relevant_summaries', params).execute()
        return response.data if response.data else []
    except Exception as e:
        return []