# File: backend/app/services/calendar/calendar_service.py
# (File Diperbarui dengan Audit Logging)

import logging
import asyncio
from uuid import UUID
from typing import List, Dict, Any, TYPE_CHECKING

# Impor Model
from app.models.user import User
from app.models.schedule import (
    Calendar, CalendarCreate, CalendarUpdate, SubscriptionRole
)
# Impor Kueri
from app.db.queries.calendar import calendar_queries
# Impor Exceptions
from app.core.exceptions import DatabaseError, NotFoundError
# --- [PENAMBAHAN BARU] ---
from app.services.audit_service import log_action # Impor Audit Service
# --- [AKHIR PENAMBAHAN] ---

if TYPE_CHECKING:
    from app.core.dependencies import AuthInfoDep

logger = logging.getLogger(__name__)

class CalendarService:
    """
    Service untuk menangani logika bisnis terkait
    manajemen Kalender (wadah/folder).
    """
    
    def __init__(self, auth_info: "AuthInfoDep"):
        self.user: User = auth_info["user"]
        self.client = auth_info["client"]
        logger.debug(f"CalendarService diinisialisasi untuk User: {self.user.id}")

    async def create_new_calendar(
        self, 
        calendar_data: CalendarCreate
    ) -> Dict[str, Any]:
        """
        Logika bisnis untuk membuat kalender baru.
        (Sekarang dengan Audit Logging).
        """
        logger.info(f"User {self.user.id} membuat kalender baru: {calendar_data.name}")
        
        payload = calendar_data.model_dump(exclude_unset=True)
        
        if payload.get("workspace_id"):
            pass # Kalender Grup
        else:
            payload["owner_user_id"] = str(self.user.id) # Kalender Pribadi

        try:
            # PANGGILAN 1: Buat Kalender
            new_calendar = await calendar_queries.create_calendar(
                self.client,
                payload
            )
            new_calendar_id = new_calendar['calendar_id']
            
            # PANGGILAN 2: Tambahkan pembuat sebagai 'owner' di Subscriptions
            await calendar_queries.create_subscription(
                self.client,
                self.user.id,
                new_calendar_id,
                SubscriptionRole.owner
            )
            
            # --- [PENAMBAHAN BARU (AUDIT)] ---
            log_action(
                user_id=self.user.id,
                action="calendar.create",
                details={
                    "calendar_id": str(new_calendar_id),
                    "name": new_calendar['name'],
                    "type": "workspace" if payload.get("workspace_id") else "personal"
                }
            )
            # --- [AKHIR PENAMBAHAN] ---
            
            logger.info(f"Kalender {new_calendar_id} berhasil dibuat dan diaudit.")
            return new_calendar

        except Exception as e:
            logger.error(f"Error di CalendarService.create_new_calendar: {e}", exc_info=True)
            if isinstance(e, DatabaseError):
                raise
            raise DatabaseError("create_new_calendar_service", str(e))

    async def get_subscribed_calendars(self) -> List[Dict[str, Any]]:
        """
        Logika bisnis untuk mengambil daftar kalender (hanya-baca, tidak perlu audit).
        """
        logger.info(f"User {self.user.id} mengambil daftar kalender (subscriptions)...")
        try:
            subscriptions_data = await calendar_queries.get_subscribed_calendars(
                self.client,
                self.user.id
            )
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
        Logika bisnis untuk memperbarui kalender.
        (Sekarang dengan Audit Logging).
        """
        logger.info(f"User {self.user.id} memperbarui kalender {calendar_id}...")
        
        payload = update_data.model_dump(exclude_unset=True)
        if not payload:
            raise ValueError("Tidak ada data untuk diperbarui.")
            
        try:
            updated_calendar = await calendar_queries.update_calendar(
                self.client,
                calendar_id,
                payload
            )
            
            # --- [PENAMBAHAN BARU (AUDIT)] ---
            log_action(
                user_id=self.user.id,
                action="calendar.update",
                details={
                    "calendar_id": str(calendar_id),
                    "changes": list(payload.keys()) # Catat field apa saja yang diubah
                }
            )
            # --- [AKHIR PENAMBAHAN] ---
            
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
        Logika bisnis untuk menghapus kalender.
        (Sekarang dengan Audit Logging).
        """
        logger.info(f"User {self.user.id} menghapus kalender {calendar_id}...")
        
        try:
            success = await calendar_queries.delete_calendar(
                self.client,
                calendar_id
            )
            
            # --- [PENAMBAHAN BARU (AUDIT)] ---
            if success:
                log_action(
                    user_id=self.user.id,
                    action="calendar.delete",
                    details={"calendar_id": str(calendar_id)}
                )
            # --- [AKHIR PENAMBAHAN] ---
            
            return success
            
        except Exception as e:
            logger.error(f"Error di CalendarService.delete_calendar: {e}", exc_info=True)
            if isinstance(e, (DatabaseError, NotFoundError)):
                raise
            raise DatabaseError("delete_calendar_service", str(e))