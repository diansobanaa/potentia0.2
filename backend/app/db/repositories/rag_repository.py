# PARSE: 97-rag-repository-holistic.py
# (Diperbarui untuk AsyncClient native)

import asyncio
import logging
from uuid import UUID
from typing import List, Tuple, Dict, Any
# --- PERBAIKAN: Impor AsyncClient ---
from supabase.client import AsyncClient
from app.db.repositories.interfaces import IRagRepository
from app.core.exceptions import RpcError
from app.core.config import settings

logger = logging.getLogger(__name__)

class SupabaseRagRepository(IRagRepository):
    """Implementasi Supabase untuk RAG holistik (async)."""

    def __init__(self, client: AsyncClient): # <-- Tipe diubah
        self.client = client

    async def find_relevant_blocks(self, embedding: List[float]) -> str:
        """(Async Native) Implementasi RPC 'find_relevant_blocks'."""
        function_name = "find_relevant_blocks"
        logger.debug(f"Memanggil RPC {function_name} holistik (mengandalkan RLS)")
        try:
            params = {
                "query_embedding": embedding,
                "match_threshold": 0.65,
                "match_count": 5
            }
            # --- PERBAIKAN: Hapus 'to_thread', gunakan 'await' ---
            response = await self.client.rpc(function_name, params).execute()

            if not response.data:
                logger.info(f"RPC {function_name} tidak menemukan blok relevan.")
                return ""

            context_lines = ["[KONTEKS BLOK RELEVAN DARI SEMUA CANVAS]"]
            for item in response.data:
                line = (
                    f"Dari Canvas '{item['canvas_title_result']}' "
                    f"(Skor: {item['similarity_score']:.2f}):\n"
                    f"{item['content_result']}\n---"
                )
                context_lines.append(line)
            
            return "\n".join(context_lines)
        except Exception as e:
            logger.error(f"Error saat memanggil RPC {function_name} (async): {e}", exc_info=True)
            raise RpcError(function_name, e)

    async def find_relevant_schedules(self, embedding: List[float]) -> str:
        """(Async Native) Implementasi RPC 'find_relevant_schedules'."""
        function_name = "find_relevant_schedules"
        logger.debug(f"Memanggil RPC {function_name} holistik (mengandalkan RLS)")
        try:
            params = {
                "query_embedding": embedding,
                "match_threshold": 0.7,
                "match_count": 5
            }
            # --- PERBAIKAN: Hapus 'to_thread', gunakan 'await' ---
            response = await self.client.rpc(function_name, params).execute()

            if not response.data:
                logger.info(f"RPC {function_name} tidak menemukan jadwal relevan.")
                return ""

            context_lines = ["[JADWAL RELEVAN YANG DITEMUKAN]"]
            for item in response.data:
                line = (
                    f"Jadwal: {item['title_result']} "
                    f"(Mulai: {item['start_time_result']}, Selesai: {item['end_time_result']}, "
                    f"Skor: {item['similarity_score']:.2f})\n"
                    f"Deskripsi: {item['description_result']}\n---"
                )
                context_lines.append(line)
            
            return "\n".join(context_lines)
        except Exception as e:
            logger.error(f"Error saat memanggil RPC {function_name} (async): {e}", exc_info=True)
            raise RpcError(function_name, e)