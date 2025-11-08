# File: backend/app/services/calendar/schedule_service.py
# (Diperbarui untuk AsyncClient native dan Validasi RRULE)

import logging
import asyncio
import pytz 
from uuid import UUID
from typing import List, Dict, Any, TYPE_CHECKING, Optional
from datetime import datetime
from fastapi import BackgroundTasks
from dateutil.rrule import rrulestr

# Impor Model
from app.models.user import User
from app.models.schedule import Schedule, ScheduleCreate, ScheduleUpdate
# Impor Kueri (sekarang async)
from app.db.queries.calendar import calendar_queries
# Impor Exceptions
from app.core.exceptions import DatabaseError, NotFoundError
# Impor Background Job
from app.jobs.schedule_expander import expand_and_populate_instances
from app.services.audit_service import log_action

if TYPE_CHECKING:
    from app.core.dependencies import AuthInfoDep
    # --- PERBAIKAN ---
    from supabase.client import AsyncClient

logger = logging.getLogger(__name__)

class ScheduleService:
    def __init__(self, auth_info: "AuthInfoDep"):
        self.user: User = auth_info["user"]
        self.client: "AsyncClient" = auth_info["client"] # <-- Tipe diubah
        logger.debug(f"ScheduleService (Async) diinisialisasi untuk User: {self.user.id}")

    # (Helper _convert_to_utc dan _convert_dt_list_to_utc_strings tidak berubah)
    def _convert_to_utc(self, dt: datetime, timezone_str: str) -> datetime:
        try:
            local_tz = pytz.timezone(timezone_str)
            if dt.tzinfo is None: aware_dt = local_tz.localize(dt)
            else: aware_dt = dt.astimezone(local_tz)
            return aware_dt.astimezone(pytz.UTC)
        except Exception as e:
            raise ValueError(f"Timezone tidak valid: {timezone_str}")

    def _convert_dt_list_to_utc_strings(
        self, dt_list: Optional[List[datetime]], timezone_str: str
    ) -> Optional[List[str]]:
        if dt_list is None: return None
        return [self._convert_to_utc(dt, timezone_str).isoformat() for dt in dt_list]

    @staticmethod
    def _normalize_rrule(rrule_raw: str, dtstart: datetime) -> str:
        """
        Mencoba memperbaiki RRULE sederhana yang sering salah ketik:
        - Menambahkan 'FREQ=' kalau tidak ada
        - Membuang baris kosong / spasi
        Jika tetap gagal, akan raise ValueError dengan pesan jelas.
        """
        if not rrule_raw or not rrule_raw.strip():
            raise ValueError("RRULE tidak boleh kosong")

        rrule_clean = rrule_raw.strip()
        # Kalau tidak ada '=', tambahkan FREQ= di depan
        if "=" not in rrule_clean:
            rrule_clean = f"FREQ={rrule_clean}"

        # Validasi ulang
        try:
            rrulestr(rrule_clean, dtstart=dtstart, forceset=True)
        except Exception as e:
            raise ValueError(f"RRULE tidak valid setelah normalisasi: {e}")
        return rrule_clean
    
    async def create_new_schedule(
        self,
        calendar_id: UUID,
        schedule_data: ScheduleCreate,
        background_tasks: BackgroundTasks
    ) -> Dict[str, Any]:
        logger.info(f"User {self.user.id} membuat acara baru di kalender {calendar_id}...")

        try:
            # --- VALIDASI RRULE (dengan fallback) ---
            if schedule_data.rrule:
                try:
                    schedule_data.rrule = self._normalize_rrule(
                        schedule_data.rrule, schedule_data.start_time
                    )
                except ValueError as ve:
                    # Ubah menjadi ValueError agar dipetakan 400 di handler
                    raise ValueError(str(ve)) from None

            # --- SISA KODE TETAP SAMA ---
            tz_str = schedule_data.original_timezone
            start_time_utc = self._convert_to_utc(schedule_data.start_time, tz_str)
            end_time_utc   = self._convert_to_utc(schedule_data.end_time, tz_str)

            payload = schedule_data.model_dump(exclude_unset=True)
            payload.update({
                "calendar_id": str(calendar_id),
                "creator_user_id": str(self.user.id),
                "start_time": start_time_utc.isoformat(),
                "end_time": end_time_utc.isoformat(),
                "rdate": self._convert_dt_list_to_utc_strings(payload.get("rdate"), tz_str),
                "exdate": self._convert_dt_list_to_utc_strings(payload.get("exdate"), tz_str),
            })
            base_metadata = {"original_timezone": tz_str}
            if schedule_data.metadata:
                base_metadata.update(schedule_data.metadata)
            payload["schedule_metadata"] = base_metadata
            payload.pop("original_timezone", None)

            new_schedule = await calendar_queries.create_schedule(self.client, payload)

            background_tasks.add_task(
                expand_and_populate_instances,
                UUID(new_schedule["schedule_id"])
            )

            await log_action(
                user_id=self.user.id,
                action="schedule.create",
                details={
                    "schedule_id": str(new_schedule["schedule_id"]),
                    "calendar_id": str(calendar_id),
                    "title": new_schedule["title"],
                },
            )
            return new_schedule

        except ValueError:
            # ValueError sudah tepat, biarkan naik sebagai 400
            raise
        except Exception as e:
            logger.error(f"Error di create_new_schedule: {e}", exc_info=True)
            raise DatabaseError("create_new_schedule_service", str(e))


    async def get_schedule_details(self, schedule_id: UUID) -> Dict[str, Any]:
        logger.info(f"User {self.user.id} mengambil detail schedule {schedule_id}...")
        try:
            # --- PERBAIKAN: Panggilan 'await' langsung ---
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
        background_tasks: BackgroundTasks,
    ) -> Dict[str, Any]:
        logger.info(f"User {self.user.id} memperbarui schedule {schedule_id}...")

        try:
            payload = update_data.model_dump(exclude_unset=True)
            payload.pop("edit_scope", None)

            # --- VALIDASI RRULE (dengan fallback) ---
            if "rrule" in payload and payload["rrule"]:
                # tentukan dtstart
                dt_start = None
                if update_data.start_time:
                    dt_start = update_data.start_time
                else:
                    # ambil dari DB
                    existing = await calendar_queries.get_schedule_by_id(self.client, schedule_id)
                    if existing:
                        dt_start = dt_parse(existing["start_time"])
                if not dt_start:
                    raise ValueError("start_time tidak ditemukan untuk validasi RRULE.")

                try:
                    payload["rrule"] = self._normalize_rrule(payload["rrule"], dt_start)
                except ValueError as ve:
                    raise ValueError(str(ve)) from None

            # --- SISA KODE TETAP SAMA ---
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

            updated_schedule = await calendar_queries.update_schedule(
                self.client, schedule_id, payload
            )

            if any(k in payload for k in ("rrule", "rdate", "exdate", "start_time")):
                background_tasks.add_task(expand_and_populate_instances, schedule_id)

            await log_action(
                user_id=self.user.id,
                action="schedule.update",
                details={"schedule_id": str(schedule_id), "changes": list(payload.keys())},
            )
            return updated_schedule

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error di update_schedule_details: {e}", exc_info=True)
            raise DatabaseError("update_schedule_service", str(e))
               
    async def delete_schedule(
        self,
        schedule_id: UUID,
        background_tasks: BackgroundTasks
    ) -> bool:
        logger.info(f"User {self.user.id} menghapus (soft delete) schedule {schedule_id}...")
        
        try:
            # Panggil Kueri (Async Native)
            await calendar_queries.soft_delete_schedule(
                self.client,
                schedule_id
            )
            
            # Memicu Background Job
            logger.info(f"Memicu background job (hapus) untuk {schedule_id}")
            background_tasks.add_task(expand_and_populate_instances, schedule_id)
            
            # Audit Log (Async)
            await log_action(
                user_id=self.user.id,
                action="schedule.delete_soft",
                details={"schedule_id": str(schedule_id)}
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error di ScheduleService.delete_schedule: {e}", exc_info=True)
            if isinstance(e, (DatabaseError, NotFoundError)):
                raise
            raise DatabaseError("delete_schedule_service", str(e))
            