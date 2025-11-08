# File: backend/app/services/calendar/guest_service.py
# (Diperbarui untuk AsyncClient native)

import logging
import asyncio
from uuid import UUID
from typing import List, Dict, Any, TYPE_CHECKING, Optional

# Impor Model
from app.models.user import User
from app.models.schedule import GuestCreate, RsvpStatus, ScheduleGuest
# Impor Kueri (sekarang async)
from app.db.queries.calendar import calendar_queries
# Impor Exceptions
from app.core.exceptions import DatabaseError, NotFoundError
from app.services.audit_service import log_action

if TYPE_CHECKING:
    from app.core.dependencies import AuthInfoDep
    # --- PERBAIKAN ---
    from supabase.client import AsyncClient

logger = logging.getLogger(__name__)

class GuestService:
    """
    Service untuk menangani logika bisnis terkait tamu (Guests).
    """
    
    def __init__(self, auth_info: "AuthInfoDep"):
        self.user: User = auth_info["user"]
        self.client: "AsyncClient" = auth_info["client"] # <-- Tipe diubah
        logger.debug(f"GuestService (Async) diinisialisasi untuk User: {self.user.id}")

    async def add_guest(
        self, 
        schedule_id: UUID,
        payload: GuestCreate
    ) -> Dict[str, Any]:
        """
        Logika bisnis untuk menambahkan tamu (async).
        """
        logger.info(f"User {self.user.id} menambahkan tamu ke acara {schedule_id}...")
        
        db_payload = {
            "schedule_id": str(schedule_id),
            "role": payload.role.value
        }
        if payload.user_id:
            db_payload["user_id"] = str(payload.user_id)
        elif payload.email:
            db_payload["guest_email"] = payload.email
        else:
            raise ValueError("Data tamu tidak valid.")

        try:
            # --- PERBAIKAN: Panggilan 'await' langsung ---
            new_guest = await calendar_queries.add_guest_to_schedule(
                self.client,
                db_payload
            )
            
            await log_action(
                user_id=self.user.id,
                action="schedule.guest_add",
                details={
                    "guest_id": str(new_guest['guest_id']),
                    "schedule_id": str(schedule_id),
                    "target": str(payload.user_id) if payload.user_id else payload.email
                }
            )
            # ---------------------------------------------
            
            return new_guest

        except Exception as e:
            logger.error(f"Error di GuestService.add_guest: {e}", exc_info=True)
            if isinstance(e, (DatabaseError, ValueError)):
                raise
            raise DatabaseError("add_guest_service", str(e))

    async def list_guests(self, schedule_id: UUID) -> List[Dict[str, Any]]:
        """
        Logika bisnis untuk mengambil daftar tamu (async).
        """
        logger.info(f"User {self.user.id} mengambil daftar tamu untuk acara {schedule_id}...")
        try:
            # --- PERBAIKAN: Panggilan 'await' langsung ---
            guests_data = await calendar_queries.get_guests_for_schedule(
                self.client,
                schedule_id
            )
            # ---------------------------------------------
            return guests_data
            
        except Exception as e:
            logger.error(f"Error di GuestService.list_guests: {e}", exc_info=True)
            raise DatabaseError("list_guests_service", str(e))

    async def respond_to_rsvp(
        self,
        schedule_id: UUID,
        user_id: UUID, 
        action: RsvpStatus
    ) -> Dict[str, Any]:
        """
        Logika bisnis untuk tamu merespons RSVP (async).
        """
        logger.info(f"Tamu {user_id} merespons '{action.value}' untuk acara {schedule_id}...")
        
        try:
            # --- PERBAIKAN: Panggilan 'await' langsung ---
            updated_guest_data = await calendar_queries.update_guest_response(
                self.client,
                schedule_id,
                user_id,
                action
            )
            
            await log_action(
                user_id=user_id,
                action="schedule.guest_rsvp",
                details={
                    "guest_id": str(updated_guest_data['guest_id']),
                    "schedule_id": str(schedule_id),
                    "response": action.value
                }
            )
            # ---------------------------------------------
            
            return updated_guest_data
            
        except Exception as e:
            logger.error(f"Error di GuestService.respond_to_rsvp: {e}", exc_info=True)
            if isinstance(e, (DatabaseError, NotFoundError)):
                raise
            raise DatabaseError("respond_to_rsvp_service", str(e))

    async def remove_guest(
        self,
        guest_id: UUID,
        # Data tamu ditambahkan dari dependency yang diperbaiki
        guest_data: Dict[str, Any] 
    ) -> bool:
        """
        Logika bisnis untuk menghapus tamu dari acara (async).
        (Sekarang menerima data tamu untuk diaudit).
        """
        logger.info(f"User {self.user.id} menghapus tamu {guest_id}...")
        
        try:
            # --- PERBAIKAN: Panggilan 'await' langsung ---
            success = await calendar_queries.remove_guest_from_schedule(
                self.client,
                guest_id
            )

            # Audit log ditambahkan (sebelumnya hilang)
            if success:
                await log_action(
                    user_id=self.user.id,
                    action="schedule.guest_remove",
                    details={
                        "guest_id": str(guest_id),
                        "schedule_id": str(guest_data.get("schedule_id")),
                        "removed_user_id": str(guest_data.get("user_id")),
                        "removed_email": guest_data.get("guest_email")
                    }
                )
            # ---------------------------------------------

            return success
            
        except Exception as e:
            logger.error(f"Error di GuestService.remove_guest: {e}", exc_info=True)
            if isinstance(e, (DatabaseError, NotFoundError)):
                raise
            raise DatabaseError("delete_guest_service", str(e))