# File: backend/app/services/notification_service.py
# (DIREFACTOR - Menghubungkan ke Redis Pub/Sub untuk SSE)

import aiosmtplib
import logging
from typing import Dict, Any, Optional
from uuid import UUID
from email.message import EmailMessage

from app.core.config import settings #
# Impor manager Pub/Sub yang telah kita buat
from app.services.redis_pubsub import redis_pubsub_manager

logger = logging.getLogger(__name__)

# --- Fungsi Email (Tidak berubah) ---
async def send_schedule_email(user_email: str, schedule_data: dict):
    #
    if not settings.SMTP_HOST:
        logger.warning("SMTP not configured. Skipping email.")
        return
    # ... (Logika aiosmtplib sama seperti di file asli)
    try:
        message = EmailMessage()
        message["From"] = settings.SMTP_USER
        message["To"] = user_email
        message["Subject"] = f"Jadwal Baru Dibuat: {schedule_data['title']}"
        message.set_content(f"Hai, jadwal baru telah dibuat untuk Anda:\n\n{schedule_data['title']}\nWaktu: {schedule_data['start_time']}")

        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            start_tls=True,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
        )
        logger.info(f"Email jadwal terkirim ke {user_email}")
    except Exception as e:
        logger.error(f"Gagal mengirim email: {e}", exc_info=True)


# --- Fungsi Notifikasi (Direfaktor) ---

async def send_notification_to_user(
    user_id: UUID, 
    title: str, 
    body: str, 
    data: Optional[Dict[str, Any]] = None
):
    """
    Mengirim notifikasi ke pengguna tertentu.
    Ini sekarang akan mendorong ke SSE via Redis.
    Sumber:
    """
    logger.info(f"Sending notification to user {user_id}: title='{title}'")
    
    # [REFACTOR] Panggil fungsi helper SSE kita
    await push_sse_notification(
        user_id=user_id,
        event_type="notification",
        payload={
            "title": title,
            "body": body,
            "data": data or {}
        }
    )

async def push_sse_notification(
    user_id: UUID, 
    event_type: str, 
    payload: dict
):
    """
    Mendorong notifikasi ke channel Redis user untuk SSE.
    (Logika ini dipindahkan dari 'notifications.py' ke service)
    """
    channel = f"user_notify:{str(user_id)}"
    message = {
        "type": event_type,
        "payload": payload
    }
    try:
        await redis_pubsub_manager.publish(channel, message)
    except Exception as e:
        logger.error(f"Gagal push SSE notification ke Redis: {e}", exc_info=True)