# backend/app/services/chat_engine/context_manager.py
import logging
import asyncio
from uuid import UUID
from typing import Dict, Any, Optional, List, Tuple
from supabase import Client
from postgrest.exceptions import APIError
from app.models.user import User 
from app.core.exceptions import DatabaseError, NotFoundError
from app.db.queries.conversation import (
    context_queries, 
    message_queries
)

logger = logging.getLogger(__name__)

class ContextManager:
    """
    Mengelola logika bisnis untuk MEMUAT dan MEMBUAT data Konteks/Memori.
    Ini adalah implementasi dari 'Memory Manager' (Subgraph s3).
    """

    def __init__(self, authed_client: Client, user: User):
        self.client = authed_client
        self.user = user

    async def load_memory_for_judge(
        self,
        conversation_id: Optional[UUID],
        context_id: Optional[UUID]
    ) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Mengimplementasikan Node n5, n6, dan n4.
        Mengambil konteks aktif saat ini DAN 50 pesan terakhirnya.
        """
        logger.debug(f"Memuat memori untuk judge (User: {self.user.id})...")
        active_context: Optional[Dict[str, Any]] = None
        messages: List[Dict[str, Any]] = []
        
        try:
            if context_id:
                # Opsi 1: Pengguna secara eksplisit meminta konteks
                logger.debug(f"Memuat context_id {context_id} secara eksplisit.")
                active_context = await asyncio.to_thread(
                    context_queries.get_context_with_summary_by_id,
                    self.client, 
                    context_id
                )
                if not active_context:
                    logger.warning(f"Context {context_id} tidak ditemukan.")
                    raise NotFoundError(f"Context {context_id} not found.")

            elif conversation_id:
                # Opsi 2: Cari konteks aktif terakhir di percakapan ini
                logger.debug(f"Mencari konteks aktif di conversation {conversation_id}.")
                active_context = await asyncio.to_thread(
                     context_queries.get_active_context_by_user,
                     self.client, 
                     self.user.id,
                     conversation_id 
                )

            if not active_context:
                # Node n5 -> Tidak (Tidak ada konteks aktif)
                logger.debug("Tidak ada konteks aktif yang ditemukan. Mengembalikan memori kosong.")
                return (None, []) # (Konteks Kosong, Pesan Kosong)

            # Node n5 -> Ya (Konteks aktif ditemukan)
            logger.debug(f"Konteks aktif ditemukan (n6): {active_context['context_id']}.")
            
            # Ambil 50 pesan terakhir (Node n4)
            messages = await asyncio.to_thread(
                message_queries.get_messages_by_context_id,
                self.client, 
                active_context['context_id'], 
                limit=50
            )
            
            return (active_context, messages)

        except Exception as e:
            logger.error(f"Error di load_memory_for_judge: {e}", exc_info=True)
            # Pastikan melempar error agar ChatService bisa menangkapnya
            if isinstance(e, (DatabaseError, NotFoundError)):
                raise
            raise DatabaseError(f"Error saat memuat memori: {str(e)}")

    async def create_new_chat_session(
        self, 
        conversation_id: UUID,
        initial_summary: str = "New chat context."
    ) -> Dict[str, Any]:
        """
        Mengeksekusi alur "New" (Node n22, n23, n24) menggunakan Python,
        bukan RPC, untuk menghindari error RLS/KeyError.
        """
        logger.debug(f"Membuat sesi chat baru (konteks) di conversation {conversation_id}.")
        try:
            # PANGGILAN 1: Buat 'context'
            new_context = await asyncio.to_thread(
                context_queries.create_context,
                self.client,
                self.user.id,
                conversation_id,
                label='user',
                status='active'
            )
            
            new_context_id = new_context['context_id']
            
            # PANGGILAN 2: Buat 'summary_memory'
            await asyncio.to_thread(
                context_queries.create_summary_for_context,
                self.client,
                self.user.id,
                new_context_id,
                initial_summary
            )
            
            # Kembalikan baris 'context' yang baru dibuat
            return new_context
            
        except Exception as e:
            logger.error(f"Gagal membuat sesi chat baru via Python: {e}", exc_info=True)
            # Jika 'context' dibuat tapi 'summary' gagal, kita punya data yatim
            # TODO: Tambahkan logika rollback jika diperlukan
            if isinstance(e, DatabaseError):
                raise
            raise DatabaseError(f"Error saat membuat sesi chat baru: {str(e)}")

    async def load_switched_context(
        self, 
        summary_id: UUID
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Mengeksekusi alur "Switch" (Node n25, n26).
        """
        logger.debug(f"Mengalihkan konteks ke summary_id {summary_id} (n25).")
        try:
            # --- PERBAIKAN: Panggil kueri yang benar ---
            switched_context = await asyncio.to_thread(
                context_queries.get_context_by_summary_id, # <-- Gunakan kueri baru
                self.client,
                summary_id
            )
            # ----------------------------------------
            
            if not switched_context:
                raise NotFoundError(f"Konteks untuk summary {summary_id} tidak ditemukan.")

            messages = await asyncio.to_thread(
                message_queries.get_messages_by_context_id,
                self.client, 
                switched_context['context_id'], 
                limit=50
            )
            
            return (switched_context, messages)
        except Exception as e:
            logger.error(f"Gagal mengalihkan konteks: {e}", exc_info=True)
            raise