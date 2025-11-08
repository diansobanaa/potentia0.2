# File: backend/app/services/calendar/calendar_service.py
# (Diperbarui untuk AsyncClient native)

import logging
import asyncio
from uuid import UUID
from typing import List, Dict, Any, TYPE_CHECKING

# Impor Model
from app.models.user import User
from app.models.schedule import (
    Calendar, CalendarCreate, CalendarUpdate, SubscriptionRole
)
# Impor Kueri (sekarang semuanya async)
from app.db.queries.calendar import calendar_queries
# Impor Exceptions
from app.core.exceptions import DatabaseError, NotFoundError
from app.services.audit_service import log_action 

if TYPE_CHECKING:
    from app.core.dependencies import AuthInfoDep
    # --- PERBAIKAN ---
    from supabase.client import AsyncClient

logger = logging.getLogger(__name__)

class CalendarService:
    """
    Service untuk menangani logika bisnis terkait
    manajemen Kalender (wadah/folder).
    """
    
    def __init__(self, auth_info: "AuthInfoDep"):
        self.user: User = auth_info["user"]
        self.client: "AsyncClient" = auth_info["client"] # <-- Tipe diubah
        logger.debug(f"CalendarService (Async) diinisialisasi untuk User: {self.user.id}")

    async def create_new_calendar(
        self, 
        calendar_data: CalendarCreate
    ) -> Dict[str, Any]:
        """
        Logika bisnis untuk membuat kalender baru.
        (Sekarang dengan panggilan DB async).
        """
        logger.info(f"User {self.user.id} membuat kalender baru: {calendar_data.name}")
        
        payload = calendar_data.model_dump(exclude_unset=True)
        
        if payload.get("workspace_id"):
            pass # Kalender Grup
        else:
            payload["owner_user_id"] = str(self.user.id) # Kalender Pribadi

        try:
            # --- PERBAIKAN: Panggilan 'await' langsung ---
            new_calendar = await calendar_queries.create_calendar(
                self.client,
                payload
            )
            new_calendar_id = new_calendar['calendar_id']
            
            await calendar_queries.create_subscription(
                self.client,
                self.user.id,
                UUID(new_calendar_id), # Pastikan UUID
                SubscriptionRole.owner
            )
            
            # Panggilan log_action sekarang harus di-await
            await log_action(
                user_id=self.user.id,
                action="calendar.create",
                details={
                    "calendar_id": str(new_calendar_id),
                    "name": new_calendar['name'],
                    "type": "workspace" if payload.get("workspace_id") else "personal"
                }
            )
            # ---------------------------------------------
            
            logger.info(f"Kalender {new_calendar_id} berhasil dibuat dan diaudit.")
            return new_calendar

        except Exception as e:
            logger.error(f"Error di CalendarService.create_new_calendar: {e}", exc_info=True)
            if isinstance(e, DatabaseError):
                raise
            raise DatabaseError("create_new_calendar_service", str(e))

    async def get_subscribed_calendars(self) -> List[Dict[str, Any]]:
        """
        Logika bisnis untuk mengambil daftar kalender (async).
        """
        logger.info(f"User {self.user.id} mengambil daftar kalender (subscriptions)...")
        try:
            # --- PERBAIKAN: Panggilan 'await' langsung ---
            subscriptions_data = await calendar_queries.get_subscribed_calendars(
                self.client,
                self.user.id
            )
            # ---------------------------------------------
            return subscriptions_data
        except Exception as e:
            logger.error(f"Error di CalendarService.get_subscribed_calendars: {e}", exc_info=True)
            raise DatabaseError("get_subscribed_calendars_service", str(e))

    async def update_calendar_details(
        self,
        calendar_id: UUID,
        update_data: CalendarUpdate
    ) -> Dict[str, Any]:
        """
        Logika bisnis untuk memperbarui kalender (async).
        """
        logger.info(f"User {self.user.id} memperbarui kalender {calendar_id}...")
        
        payload = update_data.model_dump(exclude_unset=True)
        if not payload:
            raise ValueError("Tidak ada data untuk diperbarui.")
            
        try:
            # --- PERBAIKAN: Panggilan 'await' langsung ---
            updated_calendar = await calendar_queries.update_calendar(
                self.client,
                calendar_id,
                payload
            )
            
            await log_action(
                user_id=self.user.id,
                action="calendar.update",
                details={
                    "calendar_id": str(calendar_id),
                    "changes": list(payload.keys()) 
                }
            )
            # ---------------------------------------------
            
            return updated_calendar
            
        except Exception as e:
            logger.error(f"Error di CalendarService.update_calendar_details: {e}", exc_info=True)
            if isinstance(e, (DatabaseError, NotFoundError, ValueError)):
                raise
            raise DatabaseError("update_calendar_service", str(e))

    async def delete_calendar(
        self,
        calendar_id: UUID
    ) -> bool:
        """
        Logika bisnis untuk menghapus kalender (async).
        """
        logger.info(f"User {self.user.id} menghapus kalender {calendar_id}...")
        
        try:
            # --- PERBAIKAN: Panggilan 'await' langsung ---
            success = await calendar_queries.delete_calendar(
                self.client,
                calendar_id
            )
            
            if success:
                await log_action(
                    user_id=self.user.id,
                    action="calendar.delete",
                    details={"calendar_id": str(calendar_id)}
                )
            # ---------------------------------------------
            
            return success
            
        except Exception as e:
            logger.error(f"Error di CalendarService.delete_calendar: {e}", exc_info=True)
            if isinstance(e, (DatabaseError, NotFoundError)):
                raise
            raise DatabaseError("delete_calendar_service", str(e))