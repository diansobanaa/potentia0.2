# File: backend/app/api/v1/endpoints/schedules_api.py
# (File Baru - TODO-API-3)
# (Nama file 'schedules_api.py' untuk menghindari konflik
#  dengan 'schedules.py' lama)

import logging
import pytz # Untuk validasi timezone
from fastapi import (
    APIRouter, Depends, HTTPException, 
    status, BackgroundTasks, Path
)
from typing import List, Dict, Any
from uuid import UUID

# Impor Model Pydantic
from app.models.schedule import (
    Schedule, ScheduleCreate, ScheduleUpdate, SubscriptionRole
)
# Impor Dependencies Keamanan
from app.core.dependencies import (
    CalendarEditorAccessDep, # Untuk Create
    ScheduleAccessDep,       # Untuk Read
    ScheduleServiceDep,
    get_schedule_access      # Untuk Update/Delete (Perlu custom)
)
# Impor Exceptions
from app.core.exceptions import DatabaseError, NotFoundError

logger = logging.getLogger(__name__)

# Definisikan router baru
router = APIRouter(
    tags=["schedules"] # Kita kelompokkan di tag 'schedules'
)

# =======================================================================
# === ENDPOINT RESOURCE: SCHEDULES ===
# =======================================================================

@router.post(
    "/calendars/{calendar_id}/schedules", 
    response_model=Schedule,
    status_code=status.HTTP_201_CREATED,
    summary="Buat Acara (Schedule) Baru"
)
async def create_new_schedule(
    payload: ScheduleCreate,
    background_tasks: BackgroundTasks,
    access_info: CalendarEditorAccessDep, # Keamanan: Cek 'editor'/'owner' di Kalender
    service: ScheduleServiceDep
):
    """
    Membuat acara (schedule) baru di dalam kalender tertentu.
    
    Fitur:
    - Wajib 'original_timezone' (misal: 'Asia/Jakarta').
    - Waktu dikonversi dan disimpan sebagai UTC.
    - Memicu background job untuk ekspansi RRULE (jika ada).

    KAPAN DIGUNAKAN: Di formulir pembuatan acara Kalender.
    """
    calendar_id = access_info["calendar"]["calendar_id"]
    
    # Validasi Timezone
    try:
        pytz.timezone(payload.original_timezone)
    except pytz.UnknownTimeZoneError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Timezone '{payload.original_timezone}' tidak valid."
        )

    try:
        new_schedule_data = await service.create_new_schedule(
            calendar_id, payload, background_tasks
        )
        return Schedule.model_validate(new_schedule_data) # Validasi output
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Gagal membuat acara (500) di kalender {calendar_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Error tidak terduga di create_new_schedule: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Terjadi kesalahan internal.")


@router.get(
    "/schedules/{schedule_id}", 
    response_model=Schedule,
    summary="Get Detail Acara (Schedule)"
)
async def get_schedule_details(
    access_info: ScheduleAccessDep, # Keamanan: Cek akses ke acara
    service: ScheduleServiceDep
):
    """
    Mengambil detail "sumber kebenaran" (source of truth) dari
    satu acara (schedule).
    
    Keamanan:
    Hanya pengguna yang memiliki akses ke kalender induk
    (via Owner, Workspace, atau Invite) yang dapat melihat acara ini.

    KAPAN DIGUNAKAN: Saat pengguna mengklik acara di kalender untuk melihat detail pop-up.
    """
    # Dependency 'get_schedule_access' sudah melakukan:
    # 1. Validasi Auth
    # 2. Mengambil Acara (dan 404 jika tidak ada)
    # 3. Memvalidasi Izin Kalender (dan 403 jika ditolak)
    
    # 'access_info' berisi data acara yang sudah divalidasi
    return Schedule.model_validate(access_info["schedule"])


@router.patch(
    "/schedules/{schedule_id}", 
    response_model=Schedule,
    summary="Update Acara (Schedule)"
)
async def update_schedule_details(
    schedule_id: UUID, # Ambil dari path
    payload: ScheduleUpdate,
    background_tasks: BackgroundTasks,
    service: ScheduleServiceDep,
    # Keamanan: Kita panggil dependency secara manual
    # untuk memastikan kita punya 'schedule' SEBELUM 'payload'
    access_info: Dict[str, Any] = Depends(get_schedule_access) 
):
    """
    Memperbarui detail acara (schedule).
    
    Fitur:
    - Jika 'rrule' atau 'exdate' diubah, background job akan dipicu.
    - TODO: Menangani 'edit_scope' (this vs all).
    
    Keamanan:
    Hanya 'owner' atau 'editor' dari kalender induk yang dapat
    memperbarui acara di dalamnya.
    """
    
    # 'get_schedule_access' sudah memvalidasi kita bisa 'melihat' acara.
    # Sekarang kita validasi apakah kita bisa 'mengedit'.
    user_role = access_info.get("role")
    admin_roles = [SubscriptionRole.owner.value, SubscriptionRole.editor.value] 
    
    if user_role not in admin_roles:
        logger.warning(f"Gagal update schedule (403) {schedule_id}. Role: {user_role}.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be an owner or editor of this calendar to update schedules."
        )

    try:
        updated_schedule_data = await service.update_schedule_details(
            schedule_id, payload, background_tasks
        )
        return Schedule.model_validate(updated_schedule_data)

    except ValueError as e: # Ditangkap jika payload kosong
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except NotFoundError as e:
        logger.warning(f"Gagal update schedule (404): {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Gagal update schedule (500): {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Error tidak terduga di update_schedule_details: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Terjadi kesalahan internal.")


@router.delete(
    "/schedules/{schedule_id}", 
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Hapus Acara (Schedule) (Soft Delete)"
)
async def delete_a_schedule(
    schedule_id: UUID, # Ambil dari path
    background_tasks: BackgroundTasks,
    service: ScheduleServiceDep,
    # Keamanan: Kita panggil dependency secara manual
    access_info: Dict[str, Any] = Depends(get_schedule_access)
):
    """
    Menghapus (Soft Delete) satu acara.
    
    Fitur:
    - Mengatur 'is_deleted = true'.
    - Memicu background job untuk membersihkan 'ScheduleInstances'.
    
    Keamanan:
    Hanya 'owner' atau 'editor' dari kalender induk.
    """
    
    # Validasi Izin (sama seperti PATCH)
    user_role = access_info.get("role")
    admin_roles = [SubscriptionRole.owner.value, SubscriptionRole.editor.value] 
    if user_role not in admin_roles:
        logger.warning(f"Gagal hapus schedule (403) {schedule_id}. Role: {user_role}.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be an owner or editor of this calendar to delete schedules."
        )

    try:
        await service.delete_schedule(schedule_id, background_tasks)
        return # Mengembalikan 204 No Content

    except NotFoundError as e:
        logger.warning(f"Gagal hapus schedule (404): {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Gagal hapus schedule (500): {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Error tidak terduga di delete_a_schedule: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Terjadi kesalahan internal.")