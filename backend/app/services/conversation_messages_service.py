# File: backend/app/services/conversation_messages_service.py

import logging
import asyncio
from uuid import UUID
from typing import List, Dict, Any, TYPE_CHECKING

# Gunakan TYPE_CHECKING untuk menghindari circular import
if TYPE_CHECKING:
    from app.core.dependencies import AuthInfoDep

# Impor skema baru yang akan kita buat di Langkah 3
from app.services.chat_engine.schemas import (
    PaginatedMessageListResponse, 
    MessageListItem
)
# Impor kueri baru yang kita buat di Langkah 1
from app.db.queries.conversation.message_list_queries import get_conversation_messages_paginated

logger = logging.getLogger(__name__)

class ConversationMessagesService:
    """
    Service untuk menangani logika bisnis terkait pengambilan
    daftar pesan dalam satu conversation.
    """
    
    def __init__(self, auth_info: "AuthInfoDep"):
        self.user = auth_info["user"]
        self.client = auth_info["client"]
        logger.debug(f"ConversationMessagesService diinisialisasi untuk User: {self.user.id}")

    async def get_paginated_messages(
        self, 
        conversation_id: UUID, 
        page: int, 
        size: int
    ) -> PaginatedMessageListResponse:
        """
        Mengambil daftar pesan yang dipaginasi untuk user yang sedang login
        dan conversation_id spesifik.
        """
        user_id = self.user.id
        offset = (page - 1) * size
        
        logger.info(f"User {user_id} meminta pesan: convo {conversation_id}, halaman {page}, ukuran {size}.")

        try:
            # Panggil kueri DB di thread terpisah
            messages_data, total = await asyncio.to_thread(
                get_conversation_messages_paginated,
                self.client,
                user_id,
                conversation_id,
                offset,
                size
            )
            
            # Ubah data mentah DB menjadi objek Pydantic
            message_items: List[MessageListItem] = []
            for msg in messages_data:
                message_items.append(MessageListItem(
                    message_id=msg['message_id'],
                    role=msg['role'],
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
            logger.error(f"Error di ConversationMessagesService untuk user {user_id}: {e}", exc_info=True)
            raise