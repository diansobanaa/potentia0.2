# File: backend/app/services/calendar/schedule_service.py
# (File Diperbarui dengan Audit Logging)

import logging
import asyncio
import pytz 
from uuid import UUID
from typing import List, Dict, Any, TYPE_CHECKING, Optional
from datetime import datetime
from fastapi import BackgroundTasks

# Impor Model
from app.models.user import User
from app.models.schedule import Schedule, ScheduleCreate, ScheduleUpdate
# Impor Kueri
from app.db.queries.calendar import calendar_queries
# Impor Exceptions
from app.core.exceptions import DatabaseError, NotFoundError
# Impor Background Job
from app.jobs.schedule_expander import expand_and_populate_instances
# --- [PENAMBAHAN BARU] ---
from app.services.audit_service import log_action
# --- [AKHIR PENAMBAHAN] ---

if TYPE_CHECKING:
    from app.core.dependencies import AuthInfoDep

logger = logging.getLogger(__name__)

class ScheduleService:
    """
    Service untuk menangani logika bisnis terkait
    manajemen Acara (Schedules).
    """
    
    def __init__(self, auth_info: "AuthInfoDep"):
        self.user: User = auth_info["user"]
        self.client = auth_info["client"]
        logger.debug(f"ScheduleService diinisialisasi untuk User: {self.user.id}")

    def _convert_to_utc(self, dt: datetime, timezone_str: str) -> datetime:
        """Helper untuk konversi 'naive' datetime ke UTC."""
        try:
            local_tz = pytz.timezone(timezone_str)
            if dt.tzinfo is None:
                aware_dt = local_tz.localize(dt)
            else:
                aware_dt = dt.astimezone(local_tz)
            return aware_dt.astimezone(pytz.UTC)
        except Exception as e:
            logger.error(f"Gagal konversi timezone {timezone_str}: {e}", exc_info=True)
            raise ValueError(f"Timezone tidak valid: {timezone_str}")

    def _convert_dt_list_to_utc_strings(
        self, 
        dt_list: Optional[List[datetime]], 
        timezone_str: str
    ) -> Optional[List[str]]:
        """Helper untuk konversi list[datetime] ke list[str] UTC."""
        if dt_list is None:
            return None
        return [self._convert_to_utc(dt, timezone_str).isoformat() for dt in dt_list]

    async def create_new_schedule(
        self, 
        calendar_id: UUID,
        schedule_data: ScheduleCreate,
        background_tasks: BackgroundTasks
    ) -> Dict[str, Any]:
        """
        Logika bisnis untuk membuat acara (schedule) baru.
        (Sekarang dengan Audit Logging).
        """
        logger.info(f"User {self.user.id} membuat acara baru di kalender {calendar_id}...")
        
        try:
            # 1. Konversi Waktu ke UTC
            tz_str = schedule_data.original_timezone
            start_time_utc = self._convert_to_utc(schedule_data.start_time, tz_str)
            end_time_utc = self._convert_to_utc(schedule_data.end_time, tz_str)

            # 2. Siapkan Payload Database
            payload = schedule_data.model_dump(exclude_unset=True)
            payload["calendar_id"] = str(calendar_id)
            payload["creator_user_id"] = str(self.user.id)
            payload["start_time"] = start_time_utc.isoformat()
            payload["end_time"] = end_time_utc.isoformat()
            
            # (Optimasi 2) Konversi RDATE/EXDATE ke string ISO UTC
            payload["rdate"] = self._convert_dt_list_to_utc_strings(payload.get("rdate"), tz_str)
            payload["exdate"] = self._convert_dt_list_to_utc_strings(payload.get("exdate"), tz_str)

            base_metadata = {"original_timezone": tz_str}
            if schedule_data.metadata:
                base_metadata.update(schedule_data.metadata)
            payload["schedule_metadata"] = base_metadata
            payload.pop("original_timezone", None)

            # 3. Panggil Kueri
            new_schedule = await calendar_queries.create_schedule(
                self.client,
                payload
            )
            
            # 4. Memicu Background Job (TODO-SVC-2)
            if new_schedule.get("rrule"):
                logger.info(f"Memicu background job ekspansi RRULE untuk schedule {new_schedule['schedule_id']}")
                background_tasks.add_task(
                    expand_and_populate_instances, 
                    new_schedule['schedule_id']
                )
            
            # --- [PENAMBAHAN BARU (AUDIT)] ---
            log_action(
                user_id=self.user.id,
                action="schedule.create",
                details={
                    "schedule_id": str(new_schedule['schedule_id']),
                    "calendar_id": str(calendar_id),
                    "title": new_schedule['title']
                }
            )
            # --- [AKHIR PENAMBAHAN] ---
            
            return new_schedule

        except Exception as e:
            logger.error(f"Error di ScheduleService.create_new_schedule: {e}", exc_info=True)
            if isinstance(e, (DatabaseError, ValueError)):
                raise
            raise DatabaseError("create_new_schedule_service", str(e))

    async def get_schedule_details(self, schedule_id: UUID) -> Dict[str, Any]:
        """
        Logika bisnis untuk mengambil detail satu acara (hanya-baca).
        """
        logger.info(f"User {self.user.id} mengambil detail schedule {schedule_id}...")
        try:
            schedule = await calendar_queries.get_schedule_by_id(
                self.client, schedule_id
            )
            if not schedule:
                raise NotFoundError("Acara tidak ditemukan atau telah dihapus.")
            return schedule
        except Exception as e:
            logger.error(f"Error di ScheduleService.get_schedule_details: {e}", exc_info=True)
            if isinstance(e, NotFoundError):
                raise
            raise DatabaseError("get_schedule_details_service", str(e))

    async def update_schedule_details(
        self,
        schedule_id: UUID,
        update_data: ScheduleUpdate,
        background_tasks: BackgroundTasks
    ) -> Dict[str, Any]:
        """
        Logika bisnis untuk memperbarui acara (schedule).
        (Sekarang dengan Audit Logging).
        """
        logger.info(f"User {self.user.id} memperbarui schedule {schedule_id}...")
        
        try:
            # TODO: Implementasi logika 'edit_scope' (this vs this_and_following)
            
            payload = update_data.model_dump(exclude_unset=True)
            payload.pop("edit_scope", None) 
            
            # 1. Konversi Waktu ke UTC jika ada
            tz_str = update_data.original_timezone
            if tz_str:
                if update_data.start_time:
                    payload["start_time"] = self._convert_to_utc(update_data.start_time, tz_str).isoformat()
                if update_data.end_time:
                    payload["end_time"] = self._convert_to_utc(update_data.end_time, tz_str).isoformat()
                
                payload["rdate"] = self._convert_dt_list_to_utc_strings(payload.get("rdate"), tz_str)
                payload["exdate"] = self._convert_dt_list_to_utc_strings(payload.get("exdate"), tz_str)
            
            payload.pop("original_timezone", None)
            
            if not payload:
                raise ValueError("Tidak ada data untuk diperbarui.")

            # 2. Panggil Kueri Update
            updated_schedule = await calendar_queries.update_schedule(
                self.client,
                schedule_id,
                payload
            )
            
            # 3. Memicu Background Job (jika perulangan berubah)
            if 'rrule' in payload or 'rdate' in payload or 'exdate' in payload:
                logger.info(f"Aturan perulangan berubah. Memicu background job untuk {schedule_id}")
                background_tasks.add_task(
                    expand_and_populate_instances, 
                    schedule_id
                )
            
            # --- [PENAMBAHAN BARU (AUDIT)] ---
            log_action(
                user_id=self.user.id,
                action="schedule.update",
                details={
                    "schedule_id": str(schedule_id),
                    "changes": list(payload.keys())
                }
            )
            # --- [AKHIR PENAMBAHAN] ---
            
            return updated_schedule

        except Exception as e:
            logger.error(f"Error di ScheduleService.update_schedule_details: {e}", exc_info=True)
            if isinstance(e, (DatabaseError, NotFoundError, ValueError)):
                raise
            raise DatabaseError("update_schedule_service", str(e))
            
    async def delete_schedule(
        self,
        schedule_id: UUID,
        background_tasks: BackgroundTasks
    ) -> bool:
        """
        Logika bisnis untuk menghapus acara (soft delete).
        (Sekarang dengan Audit Logging).
        """
        logger.info(f"User {self.user.id} menghapus (soft delete) schedule {schedule_id}...")
        
        try:
            # 1. Lakukan Soft Delete
            await calendar_queries.soft_delete_schedule(
                self.client,
                schedule_id
            )
            
            # 2. Memicu Background Job (untuk membersihkan instances)
            logger.info(f"Memicu background job (hapus) untuk {schedule_id}")
            background_tasks.add_task(
                expand_and_populate_instances, 
                schedule_id
            )
            
            # --- [PENAMBAHAN BARU (AUDIT)] ---
            log_action(
                user_id=self.user.id,
                action="schedule.delete_soft",
                details={"schedule_id": str(schedule_id)}
            )
            # --- [AKHIR PENAMBAHAN] ---
            
            return True
            
        except Exception as e:
            logger.error(f"Error di ScheduleService.delete_schedule: {e}", exc_info=True)
            if isinstance(e, (DatabaseError, NotFoundError)):
                raise
            raise DatabaseError("delete_schedule_service", str(e))