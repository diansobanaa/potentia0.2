# File: backend/app/services/conversations_list_service.py

import logging
import asyncio
from uuid import UUID
from typing import List, Dict, Any, TYPE_CHECKING

# Gunakan TYPE_CHECKING untuk menghindari circular import
if TYPE_CHECKING:
    from app.core.dependencies import AuthInfoDep

from app.services.chat_engine.schemas import (
    PaginatedConversationListResponse, 
    ConversationListItem
)
from app.db.queries.conversation.conversation_list_queries import get_user_conversations_paginated

logger = logging.getLogger(__name__)

class ConversationListService:
    """
    Service untuk menangani logika bisnis terkait daftar conversation.
    """
    
    # Gunakan string literal untuk type hint pada parameter
    def __init__(self, auth_info: "AuthInfoDep"):
        """
        Mengikuti pola ChatService, menerima dependency yang diperlukan.
        """
        self.user = auth_info["user"]
        self.client = auth_info["client"]
        logger.debug(f"ConversationListService diinisialisasi untuk User: {self.user.id}")

    async def get_paginated_conversations(self, page: int, size: int) -> PaginatedConversationListResponse:
        """
        Mengambil daftar conversation yang dipaginasi untuk user yang sedang login.
        """
        user_id = self.user.id
        offset = (page - 1) * size
        
        logger.info(f"User {user_id} meminta daftar conversation: halaman {page}, ukuran {size}.")

        try:
            conversations_data, total = await asyncio.to_thread(
                get_user_conversations_paginated,
                self.client,
                user_id,
                offset,
                size
            )
            
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
            logger.error(f"Error di ConversationListService untuk user {user_id}: {e}", exc_info=True)
            raise