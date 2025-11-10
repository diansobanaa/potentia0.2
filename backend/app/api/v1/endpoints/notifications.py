# File: backend/api/v1/endpoints/notifications.py
# (DIREFACTOR - Perbaikan Skalabilitas SSE dengan Redis Pub/Sub)

import logging
import asyncio
from uuid import UUID
import json
from fastapi import APIRouter, Depends, HTTPException, Request
from sse_starlette.sse import EventSourceResponse # Perlu 'pip install sse-starlette'

from app.models.user import User
from app.core.dependencies import get_current_user
from app.services.notification_service import send_notification_to_user #

# [REFACTOR] Impor manager Pub/Sub
from app.services.redis_pubsub import redis_pubsub_manager

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/notifications",
    tags=["notifications"]
)

# -----------------------------------------------------------------
# !! DIHAPUS !!
# Global dictionary 'active_sse_connections'
# telah dihapus untuk mendukung Redis Pub/Sub.
# -----------------------------------------------------------------

@router.get("/stream")
async def notifications_stream(
    request: Request, 
    current_user: User = Depends(get_current_user)
):
    """
    Endpoint untuk koneksi Server-Sent Events (SSE).
    Sekarang menggunakan Redis Pub/Sub untuk skalabilitas.
    """
    user_id = str(current_user.id)
    # Setiap user memiliki channel Redis pribadi untuk notifikasi
    channel = f"user_notify:{user_id}"

    async def event_stream():
        """Menghasilkan event dari Redis Pub/Sub."""
        try:
            # Dengarkan channel pribadi user
            async for message in redis_pubsub_manager.subscribe(channel):
                # Cek jika client masih terhubung
                if await request.is_disconnected():
                    logger.info(f"SSE client {user_id} disconnected (request check).")
                    break
                
                # Format pesan sebagai event SSE
                yield {
                    "event": message.get("type", "notification"),
                    "data": json.dumps(message.get("payload", {}))
                }
        except asyncio.CancelledError:
            logger.info(f"SSE stream untuk user {user_id} dibatalkan.")
        except Exception as e:
            logger.error(f"Error di SSE stream untuk {user_id}: {e}", exc_info=True)
    
    return EventSourceResponse(event_stream())

# --- Fungsi Helper (Baru) ---
# (Ini harus dipindahkan ke 'notification_service.py' nanti)

async def push_sse_notification(user_id: UUID, event_type: str, payload: dict):
    """
    Mendorong notifikasi ke channel Redis user.
    """
    channel = f"user_notify:{str(user_id)}"
    message = {
        "type": event_type,
        "payload": payload
    }
    await redis_pubsub_manager.publish(channel, message)