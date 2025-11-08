# File: backend/app/services/calendar/view_service.py
# (Diperbarui untuk AsyncClient native)

import logging
import asyncio
from uuid import UUID
from typing import List, Dict, Any, TYPE_CHECKING
from datetime import datetime

# Impor Model
from app.models.user import User
from app.models.schedule import ScheduleInstance
from pydantic import BaseModel

# Impor Kueri (sekarang async)
from app.db.queries.calendar import calendar_queries
# Impor Exceptions
from app.core.exceptions import DatabaseError

if TYPE_CHECKING:
    from app.core.dependencies import AuthInfoDep
    # --- PERBAIKAN ---
    from supabase.client import AsyncClient

logger = logging.getLogger(__name__)

class PaginatedScheduleInstanceResponse(BaseModel):
    items: List[ScheduleInstance]
    total: int
    page: int
    size: int
    total_pages: int

class ViewService:
    """
    Service untuk menangani logika bisnis terkait Tampilan (Views) kalender.
    """
    
    def __init__(self, auth_info: "AuthInfoDep"):
        self.user: User = auth_info["user"]
        self.client: "AsyncClient" = auth_info["client"] # <-- Tipe diubah
        logger.debug(f"ViewService (Async) diinisialisasi untuk User: {self.user.id}")

    async def get_paginated_schedule_view(
        self, 
        start_time: datetime,
        end_time: datetime,
        page: int, 
        size: int
    ) -> PaginatedScheduleInstanceResponse:
        """
        Logika bisnis untuk 'GET /view/schedules' (async).
        """
        user_id = self.user.id
        offset = (page - 1) * size
        
        logger.info(f"User {user_id} meminta tampilan jadwal: page {page}, size {size}")

        try:
            # --- PERBAIKAN: Panggilan 'await' langsung ---
            # Kueri ini sudah dioptimalkan dengan asyncio.gather di dalamnya
            instances_data, total = await calendar_queries.get_schedule_instances_for_user(
                self.client,
                user_id,
                start_time,
                end_time,
                size, # 'limit'
                offset
            )
            # ---------------------------------------------
            
            instance_items = [
                ScheduleInstance.model_validate(inst) for inst in instances_data
            ]

            total_pages = (total + size - 1) // size
            
            logger.info(f"Berhasil mengambil {len(instance_items)} instance dari total {total} untuk user {user_id}.")

            return PaginatedScheduleInstanceResponse(
                items=instance_items,
                total=total,
                page=page,
                size=size,
                total_pages=total_pages
            )

        except Exception as e:
            logger.error(f"Error di ViewService.get_paginated_schedule_view: {e}", exc_info=True)
            raise DatabaseError("get_paginated_schedule_view_service", str(e))