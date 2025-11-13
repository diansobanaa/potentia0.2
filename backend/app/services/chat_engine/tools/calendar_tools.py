# File: backend/app/services/chat_engine/tools/calendar_tools.py
# (Diperbarui v2.7 - Menyelesaikan NFR Poin 5: Idempotency)

import logging
from uuid import UUID
from datetime import datetime
from fastapi import BackgroundTasks
from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool

# Impor Service Kalender yang sudah ada (dari file Anda)
from app.services.calendar.schedule_service import ScheduleService
from app.models.schedule import ScheduleCreate
# [BARU v2.7] Impor klien Redis untuk idempotency lock
from app.services.redis_rate_limiter import rate_limiter

logger = logging.getLogger(__name__)

class CreateScheduleToolInput(BaseModel):
    # ... (Skema tidak berubah)
    title: str = Field(..., description="Judul acara.")
    start_time: datetime = Field(..., description="Waktu mulai acara (ISO format).")
    end_time: datetime = Field(..., description="Waktu selesai acara (ISO format).")
    original_timezone: str = Field(default="Asia/Jakarta", description="Timezone IANA, misal: 'Asia/Jakarta'.")
    calendar_id: str = Field(..., description="ID kalender (UUID) tempat acara akan dibuat.")


async def _create_schedule_tool_implementation( # <-- UBAH NAMA (tambah _)
    schedule_service: ScheduleService,
    title: str,
    start_time: datetime,
    end_time: datetime,
    calendar_id: str,
    background_tasks: BackgroundTasks,
    original_timezone: str = "Asia/Jakarta",
    request_id: str = "N/A"
) -> str:
    """
    Implementasi logika tool untuk membuat jadwal (schedule) baru.
    (v2.7: Sekarang Idempotent menggunakan request_id)
    """
    logger.info(f"REQUEST_ID: {request_id} - Tool 'create_schedule_tool' dipanggil: {title}")
    
    # === [BARU v2.7] Implementasi Idempotency (NFR Poin 5) ===
    lock_key = f"lock:tool:{request_id}"
    try:
        is_new_request = await rate_limiter.redis.set(lock_key, "1", nx=True, ex=3600)
        if not is_new_request:
            logger.warning(f"REQUEST_ID: {request_id} - Terdeteksi duplikat, eksekusi tool dibatalkan.")
            return f"Info: Permintaan untuk membuat jadwal '{title}' sudah diproses sebelumnya."
    except Exception as e:
        logger.error(f"REQUEST_ID: {request_id} - Gagal mengecek idempotency lock di Redis: {e}. Melanjutkan eksekusi...")
    
    try:
        cal_uuid = UUID(calendar_id)
        
        payload = ScheduleCreate(
            title=title,
            start_time=start_time,
            end_time=end_time,
            original_timezone=original_timezone
        )
        
        new_schedule = await schedule_service.create_new_schedule(
            calendar_id=cal_uuid,
            schedule_data=payload,
            background_tasks=background_tasks
        )
        
        return f"Sukses: Jadwal '{new_schedule['title']}' berhasil dibuat dengan ID: {new_schedule['schedule_id']}"

    except Exception as e:
        logger.error(f"REQUEST_ID: {request_id} - Error saat eksekusi create_schedule_tool: {e}", exc_info=True)
        await rate_limiter.redis.delete(lock_key)
        return f"Error: Gagal membuat jadwal. {e}"
    
# [PERBAIKAN] Buat instance StructuredTool
# Ini adalah apa yang akan dilihat oleh LLM.
create_schedule_tool = StructuredTool(
    name="create_schedule_tool",
    description="Tool untuk membuat jadwal (schedule) baru di kalender pengguna.",
    func=_create_schedule_tool_implementation,
    args_schema=CreateScheduleToolInput
)