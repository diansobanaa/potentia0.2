# File: backend/app/services/conversation_messages_service.py
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
    PaginatedMessageListResponse, 
    MessageListItem
)
from app.db.queries.conversation.message_list_queries import get_conversation_messages_paginated

logger = logging.getLogger(__name__)

class ConversationMessagesService:
    def __init__(self, auth_info: "AuthInfoDep"):
        self.user = auth_info["user"]
        self.client: "AsyncClient" = auth_info["client"] # <-- Tipe diubah
        logger.debug(f"ConversationMessagesService (Async) diinisialisasi untuk User: {self.user.id}")

    async def get_paginated_messages(
        self, 
        conversation_id: UUID, 
        page: int, 
        size: int
    ) -> PaginatedMessageListResponse:
        user_id = self.user.id
        offset = (page - 1) * size
        
        logger.info(f"User {user_id} meminta pesan: convo {conversation_id}, halaman {page}, ukuran {size}.")

        try:
            # --- PERBAIKAN: Hapus 'to_thread', panggil 'await' langsung ---
            # (Kueri ini sudah dioptimalkan dengan asyncio.gather di dalamnya)
            messages_data, total = await get_conversation_messages_paginated(
                self.client,
                user_id,
                conversation_id,
                offset,
                size
            )
            # ---------------------------------------------
            
            message_items: List[MessageListItem] = []
            for msg in messages_data:
                # Map 'ai' role to 'assistant' to satisfy Pydantic validation
                role = msg['role']
                if role == 'ai':
                    role = 'assistant'
                message_items.append(MessageListItem(
                    message_id=msg['message_id'],
                    role=role,
                    content=msg['content'],
                    created_at=msg['created_at']
                ))

            total_pages = (total + size - 1) // size
            
            logger.info(f"Berhasil mengambil {len(message_items)} pesan dari total {total} untuk convo {conversation_id}.")

            return PaginatedMessageListResponse(
                items=message_items,
                total=total,
                page=page,
                size=size,
                total_pages=total_pages
            )

        except Exception as e:
            logger.error(f"Error di ConversationMessagesService (async) untuk user {user_id}: {e}", exc_info=True)
            raise