# File: backend/app/services/conversations_list_service.py
# (Diperbarui untuk AsyncClient native)

import logging
import asyncio
from uuid import UUID
from typing import List, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.dependencies import AuthInfoDep
    # --- PERBAIKAN ---
    from supabase.client import AsyncClient

from app.services.chat_engine.schemas import (
    PaginatedConversationListResponse, 
    ConversationListItem
)
from app.db.queries.conversation.conversation_list_queries import get_user_conversations_paginated

logger = logging.getLogger(__name__)

class ConversationListService:
    def __init__(self, auth_info: "AuthInfoDep"):
        self.user = auth_info["user"]
        self.client: "AsyncClient" = auth_info["client"] # <-- Tipe diubah
        logger.debug(f"ConversationListService (Async) diinisialisasi untuk User: {self.user.id}")

    async def get_paginated_conversations(self, page: int, size: int) -> PaginatedConversationListResponse:
        user_id = self.user.id
        offset = (page - 1) * size
        
        logger.info(f"User {user_id} meminta daftar conversation: halaman {page}, ukuran {size}.")

        try:
            # --- PERBAIKAN: Hapus 'to_thread', panggil 'await' langsung ---
            # (Kueri ini sudah dioptimalkan dengan asyncio.gather di dalamnya)
            conversations_data, total = await get_user_conversations_paginated(
                self.client,
                user_id,
                offset,
                size
            )
            # ---------------------------------------------
            
            conversation_items: List[ConversationListItem] = []
            for conv in conversations_data:
                title = conv.get('title') or "New Conversation"
                conversation_items.append(ConversationListItem(
                    conversation_id=conv['conversation_id'],
                    title=title,
                    updated_at=conv['updated_at']
                ))

            total_pages = (total + size - 1) // size

            logger.info(f"Berhasil mengambil {len(conversation_items)} conversation dari total {total}.")

            return PaginatedConversationListResponse(
                items=conversation_items,
                total=total,
                page=page,
                size=size,
                total_pages=total_pages
            )

        except Exception as e:
            logger.error(f"Error di ConversationListService (async) untuk user {user_id}: {e}", exc_info=True)
            raise