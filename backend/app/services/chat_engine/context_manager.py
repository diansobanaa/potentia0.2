# backend/app/services/chat_engine/context_manager.py
# (Diperbarui untuk panggilan query async native)

import logging
import asyncio
from uuid import UUID
from typing import Dict, Any, Optional, List, Tuple
# --- PERBAIKAN: Impor AsyncClient ---
from supabase.client import AsyncClient
from postgrest.exceptions import APIError
from app.models.user import User 
from app.core.exceptions import DatabaseError, NotFoundError
from app.db.queries.conversation import (
    context_queries, 
    message_queries
)

logger = logging.getLogger(__name__)

class ContextManager:
    def __init__(self, authed_client: AsyncClient, user: User): # <-- Tipe diubah
        self.client = authed_client
        self.user = user

    async def load_memory_for_judge(
        self,
        conversation_id: Optional[UUID],
        context_id: Optional[UUID]
    ) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        logger.debug(f"Memuat memori untuk judge (User: {self.user.id})...")
        active_context: Optional[Dict[str, Any]] = None
        messages: List[Dict[str, Any]] = []
        
        try:
            # --- PERBAIKAN: Hapus 'asyncio.to_thread' ---
            if context_id:
                logger.debug(f"Memuat context_id {context_id} secara eksplisit.")
                active_context = await context_queries.get_context_with_summary_by_id(
                    self.client, 
                    context_id
                ) # <-- 'await'
                if not active_context:
                    raise NotFoundError(f"Context {context_id} not found.")

            elif conversation_id:
                logger.debug(f"Mencari konteks aktif di conversation {conversation_id}.")
                active_context = await context_queries.get_active_context_by_user(
                     self.client, 
                     self.user.id,
                     conversation_id 
                ) # <-- 'await'

            if not active_context:
                logger.debug("Tidak ada konteks aktif yang ditemukan. Mengembalikan memori kosong.")
                return (None, []) 

            logger.debug(f"Konteks aktif ditemukan (n6): {active_context['context_id']}.")
            
            messages = await message_queries.get_messages_by_context_id(
                self.client, 
                active_context['context_id'], 
                limit=50
            ) # <-- 'await'
            
            return (active_context, messages)

        except Exception as e:
            logger.error(f"Error di load_memory_for_judge (async): {e}", exc_info=True)
            if isinstance(e, (DatabaseError, NotFoundError)):
                raise
            raise DatabaseError(f"Error saat memuat memori: {str(e)}")

    async def create_new_chat_session(
        self, 
        conversation_id: UUID,
        initial_summary: str = "New chat context."
    ) -> Dict[str, Any]:
        logger.debug(f"Membuat sesi chat baru (konteks) di conversation {conversation_id}.")
        try:
            # --- PERBAIKAN: Hapus 'asyncio.to_thread' ---
            new_context = await context_queries.create_context(
                self.client,
                self.user.id,
                conversation_id,
                label='user',
                status='active'
            ) # <-- 'await'
            
            new_context_id = new_context['context_id']
            
            await context_queries.create_summary_for_context(
                self.client,
                self.user.id,
                new_context_id,
                initial_summary
            ) # <-- 'await'
            
            return new_context
            
        except Exception as e:
            logger.error(f"Gagal membuat sesi chat baru via Python (async): {e}", exc_info=True)
            if isinstance(e, DatabaseError):
                raise
            raise DatabaseError(f"Error saat membuat sesi chat baru: {str(e)}")

    async def load_switched_context(
        self, 
        summary_id: UUID
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        logger.debug(f"Mengalihkan konteks ke summary_id {summary_id} (n25).")
        try:
            # --- PERBAIKAN: Hapus 'asyncio.to_thread' ---
            switched_context = await context_queries.get_context_by_summary_id(
                self.client,
                summary_id
            ) # <-- 'await'
            
            if not switched_context:
                raise NotFoundError(f"Konteks untuk summary {summary_id} tidak ditemukan.")

            messages = await message_queries.get_messages_by_context_id(
                self.client, 
                switched_context['context_id'], 
                limit=50
            ) # <-- 'await'
            
            return (switched_context, messages)
        except Exception as e:
            logger.error(f"Gagal mengalihkan konteks: {e}", exc_info=True)
            raise