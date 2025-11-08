# File: backend/app/api/v1/endpoints/schedule_guests.py
# (File Baru - TODO-API-5)

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from uuid import UUID

# Impor Model Pydantic
from app.models.schedule import (
    GuestCreate, ScheduleGuest, RsvpStatus
)

# Impor Dependencies Keamanan
from app.core.dependencies import (
    ScheduleAccessDep,       # Untuk GET, POST, DELETE
    GuestAccessDep,          # Untuk RSVP
    GuestServiceDep
)
# Impor Exceptions
from app.core.exceptions import DatabaseError, NotFoundError
# Impor Role (untuk cek 'editor')
from app.models.schedule import SubscriptionRole

logger = logging.getLogger(__name__)

# Definisikan router baru
router = APIRouter(
    prefix="/schedules/{schedule_id}/guests",
    tags=["schedules"] # Kita kelompokkan di tag 'schedules'
)

# =======================================================================
# === ENDPOINT RESOURCE: GUESTS (RSVP) ===
# =======================================================================

@router.post(
    "/", 
    response_model=ScheduleGuest,
    status_code=status.HTTP_201_CREATED,
    summary="Tambah Tamu ke Acara"
)
async def add_guest_to_a_schedule(
    schedule_id: UUID, # Diambil dari path prefix
    payload: GuestCreate,
    access_info: ScheduleAccessDep, # Keamanan: Cek akses ke Acara
    service: GuestServiceDep
):
    """
    Menambahkan tamu (via email atau user_id) ke satu acara.
    
    Keamanan:
    Hanya 'owner' atau 'editor' dari kalender induk yang dapat
    menambahkan tamu.
    """
    
    # Validasi Izin (Manual): Cek role dari dependency
    user_role = access_info.get("role")
    admin_roles = [SubscriptionRole.owner.value, SubscriptionRole.editor.value] 
    if user_role not in admin_roles:
        logger.warning(f"Gagal tambah tamu (403) ke {schedule_id}. Role: {user_role}.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hanya 'owner' atau 'editor' kalender yang bisa menambah tamu."
        )
        
    try:
        new_guest_data = await service.add_guest(schedule_id, payload)
        return ScheduleGuest.model_validate(new_guest_data) # Validasi output
        
    except DatabaseError as e:
        logger.error(f"Gagal menambah tamu (500) ke {schedule_id}: {e}", exc_info=True)
        if "invite_conflict" in str(e):
             raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, 
                detail="Tamu ini sudah diundang ke acara tersebut."
            )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error tidak terduga di add_guest_to_a_schedule: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Terjadi kesalahan internal.")


@router.get(
    "/", 
    response_model=List[ScheduleGuest], # TODO: Buat response model yg lebih baik
    summary="List Tamu di Acara"
)
async def list_guests_for_a_schedule(
    schedule_id: UUID, # Diambil dari path prefix
    access_info: ScheduleAccessDep, # Keamanan: Cek akses (viewer)
    service: GuestServiceDep
):
    """
    Mengambil daftar semua tamu yang diundang ke acara ini.
    
    Keamanan:
    Hanya pengguna yang sudah memiliki akses (minimal 'viewer')
    ke kalender induk yang dapat melihat daftar tamu.
    """
    try:
        guests = await service.list_guests(schedule_id)
        return [ScheduleGuest.model_validate(g) for g in guests]
        
    except Exception as e:
        logger.error(f"Gagal mengambil daftar tamu: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Terjadi kesalahan internal.")


@router.patch(
    "/respond", 
    response_model=ScheduleGuest,
    summary="Respons Undangan (RSVP)"
)
async def respond_to_schedule_invite(
    schedule_id: UUID, # Diambil dari path prefix
    action: RsvpStatus, # Cukup kirim "accepted" atau "declined"
    access_info: GuestAccessDep, # Keamanan: Cek apakah user adalah tamu 'pending'
    service: GuestServiceDep
):
    """
    Endpoint untuk PENGGUNA YANG LOGIN (TAMU) merespons
    undangan acara (RSVP: accept/decline).
    
    Keamanan:
    Dependency 'GuestAccessDep' memastikan bahwa pengguna yang login
    adalah tamu yang valid untuk 'schedule_id' ini DAN
    status undangannya masih 'pending'.
    """
    user_id = access_info["user"].id
    
    try:
        updated_guest = await service.respond_to_rsvp(
            schedule_id, user_id, action
        )
        return ScheduleGuest.model_validate(updated_guest)
        
    except NotFoundError as e:
        logger.warning(f"Gagal RSVP (404) ke {schedule_id}: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Gagal RSVP (500) ke {schedule_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Error tidak terduga di respond_to_schedule_invite: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Terjadi kesalahan internal.")


@router.delete(
    "/{guest_id}", 
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Hapus/Keluarkan Tamu dari Acara"
)
async def remove_guest_from_a_schedule(
    schedule_id: UUID, # Diambil dari path prefix
    guest_id: UUID,
    access_info: ScheduleAccessDep, # Keamanan: Cek akses ke Acara
    service: GuestServiceDep
):
    """
    Menghapus tamu dari acara.
    
    Keamanan:
    Hanya 'owner' atau 'editor' dari kalender induk yang dapat
    mengeluarkan tamu.
    """
    
    # Validasi Izin (Manual)
    user_role = access_info.get("role")
    admin_roles = [SubscriptionRole.owner.value, SubscriptionRole.editor.value] 
    if user_role not in admin_roles:
        logger.warning(f"Gagal hapus tamu (403) dari {schedule_id}. Role: {user_role}.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hanya 'owner' atau 'editor' kalender yang bisa menghapus tamu."
        )

    try:
        await service.remove_guest(guest_id)
        return # Mengembalikan 204 No Content

    except NotFoundError as e:
        logger.warning(f"Gagal hapus tamu (404) dari {schedule_id}: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Gagal hapus tamu (500) dari {schedule_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Error tidak terduga di remove_guest_from_a_schedule: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Terjadi kesalahan internal.")