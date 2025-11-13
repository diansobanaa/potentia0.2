# File: backend/app/services/chat_engine/tools/rag_tools.py
# (File Baru - Rencana v2.1 Fase 3)

import logging
from typing import List, Dict, Any
from uuid import UUID
from supabase.client import AsyncClient

from app.services.embedding_service import GeminiEmbeddingService

logger = logging.getLogger(__name__)

async def retrieve_relevant_history(
    query: str, 
    request_id: str,
    # --- Parameter Internal (Injeksi dari State) ---
    user_id: str,
    authed_client: AsyncClient,
    embedding_service: GeminiEmbeddingService
) -> List[Dict[str, Any]]:
    """
    Tool untuk RAG Riwayat (Goal #2).
    Memanggil RPC 'find_relevant_history_v2'.
    """
    logger.info(f"REQUEST_ID: {request_id} - Tool 'retrieve_relevant_history' dipanggil.")
    try:
        query_embedding = await embedding_service.generate_embedding(
            text=query, 
            task_type="retrieval_query"
        )
        
        response = await authed_client.rpc(
            "find_relevant_history_v2",
            {
                "p_user_id": user_id,
                "p_query_embedding": query_embedding,
                "p_match_threshold": 0.5, # Threshold lebih rendah (Goal #2)
                "p_match_count": 5
            }
        ).execute()
        
        return response.data or []
    except Exception as e:
        logger.error(f"REQUEST_ID: {request_id} - Error di retrieve_relevant_history: {e}")
        return [{"error": f"Gagal mengambil riwayat: {e}"}]

async def retrieve_relevant_blocks(
    query: str, 
    request_id: str,
    # --- Parameter Internal (Injeksi dari State) ---
    user_id: str,
    authed_client: AsyncClient,
    embedding_service: GeminiEmbeddingService
) -> List[Dict[str, Any]]:
    """
    Tool untuk RAG Canvas Holistik (Goal #2).
    Memanggil RPC 'find_relevant_blocks_holistic'.
    """
    logger.info(f"REQUEST_ID: {request_id} - Tool 'retrieve_relevant_blocks' dipanggil.")
    try:
        query_embedding = await embedding_service.generate_embedding(
            text=query, 
            task_type="retrieval_query"
        )
        
        # Memanggil RPC baru yang RLS-enabled (Holistic)
        response = await authed_client.rpc(
            "find_relevant_blocks_holistic",
            {
                "p_query_embedding": query_embedding,
                "p_match_threshold": 0.5,
                "p_match_count": 10 # Ambil lebih banyak untuk di-rerank
            }
        ).execute()
        
        return response.data or []
    except Exception as e:
        logger.error(f"REQUEST_ID: {request_id} - Error di retrieve_relevant_blocks: {e}")
        return [{"error": f"Gagal mengambil blok canvas: {e}"}]