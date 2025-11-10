# File: backend/app/services/broadcast.py
# (DIREFACTOR)

import json
import logging
from typing import Dict, Any, Optional
from uuid import UUID

# Impor service Pub/Sub yang baru
from app.services.redis_pubsub import redis_pubsub_manager

logger = logging.getLogger(__name__)


async def broadcast_to_canvas(
    canvas_id: UUID, 
    message: Dict[str, Any], 
    exclude_user_id: Optional[UUID] = None
):
    """
    Helper function to broadcast a message to all connected users in a canvas
    via Redis Pub/Sub.
    """
    channel = f"canvas:{str(canvas_id)}"
    
    # Tambahkan 'exclude_user_id' ke payload jika ada
    # 'socket.py' (subscriber) akan bertanggung jawab untuk tidak mengirimkannya.
    if exclude_user_id:
        message["_exclude_user_id"] = str(exclude_user_id)
        
    await redis_pubsub_manager.publish(channel, message)