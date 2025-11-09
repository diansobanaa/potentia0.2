# File: backend/app/api/v1/endpoints/calendars.py
# (File Baru - TODO-API-2)

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from uuid import UUID

# Impor Model Pydantic
from app.models.schedule import (
    Calendar, CalendarCreate, CalendarUpdate
)
# Impor Model Respons
from app.models.workspace import WorkspaceMemberResponse # (Kita bisa buat yg baru nanti)

# Impor Dependencies Keamanan
from app.core.dependencies import (
    AuthInfoDep,
    CalendarAccessDep,
    CalendarEditorAccessDep,
    CalendarServiceDep
)
# Impor Exceptions
from app.core.exceptions import DatabaseError, NotFoundError

logger = logging.getLogger(__name__)

# Definisikan router baru
router = APIRouter(
    prefix="/calendars",
    tags=["calendars"]
)

# =======================================================================
# === ENDPOINT RESOURCE: CALENDARS ===
# =======================================================================

@router.post(
    "/", 
    response_model=Calendar,
    status_code=status.HTTP_201_CREATED,
    summary="Buat Kalender Baru"
)
async def create_new_calendar(
    payload: CalendarCreate,
    service: CalendarServiceDep, # Menggunakan service
    auth_info: AuthInfoDep       # Diperlukan oleh service
):
    """
    Membuat "wadah" kalender baru. Pembuat otomatis ditambahkan sebagai 'owner'
    
    Fitur:
    - Jika 'workspace_id' disediakan, kalender ini milik workspace.
    - Jika tidak, kalender ini bersifat pribadi ('owner_user_id' diisi otomatis).
    - Pembuat otomatis ditambahkan sebagai 'owner' di 'CalendarSubscriptions'.
    
    INPUT: CalendarCreate (name: str, workspace_id: Optional[UUID]).
    OUTPUT: Calendar (ID, name, owner/workspace ID).
    
    KAPAN DIGUNAKAN: Di UI Kalender saat pengguna membuat kalender baru.
    """
    try:
        new_calendar_data = await service.create_new_calendar(payload)
        return Calendar.model_validate(new_calendar_data) # Validasi output
        
    except DatabaseError as e:
        logger.error(f"Gagal membuat kalender (500): {e}", exc_info=True)
        if "check_owner_or_workspace" in str(e):
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Kalender tidak boleh memiliki owner_user_id dan workspace_id sekaligus."
            )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Error tidak terduga di create_new_calendar: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Terjadi kesalahan internal.")

@router.get(
    "/", 
    response_model=List[Dict[str, Any]], # TODO: Buat response model yg lebih baik
    summary="List Kalender Saya (yang di-subscribe)"
)
async def get_my_subscribed_calendars(
    service: CalendarServiceDep, # Menggunakan service
    auth_info: AuthInfoDep       # Diperlukan oleh service
):
    """
    Mengambil daftar semua kalender yang di-subscribe oleh pengguna.
    
    Fitur:
    Ini mengembalikan 'role' pengguna di kalender tersebut 
    beserta detail kalendernya (JOIN).
    """
    try:
        subscriptions = await service.get_subscribed_calendars()
        # TODO: Parsing ini ke response model yang bersih
        return subscriptions
        
    except Exception as e:
        logger.error(f"Gagal mengambil daftar kalender: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Terjadi kesalahan internal.")

@router.patch(
    "/{calendar_id}", 
    response_model=Calendar,
    summary="Perbarui Kalender"
)
async def update_calendar_details(
    payload: CalendarUpdate,
    access_info: CalendarEditorAccessDep, # Keamanan: Cek 'editor'/'owner'
    service: CalendarServiceDep
):
    """
    Memperbarui detail kalender (nama, warna, visibilitas).
    
    Keamanan:
    Hanya 'owner' atau 'editor' yang dapat memperbarui.
    """
    calendar_id = access_info["calendar"]["calendar_id"]
    
    try:
        updated_calendar_data = await service.update_calendar_details(
            calendar_id, payload
        )
        return Calendar.model_validate(updated_calendar_data) # Validasi output

    except ValueError as e: # Ditangkap jika payload kosong
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except NotFoundError as e:
        logger.warning(f"Gagal update kalender (404): {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Gagal update kalender (500): {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Error tidak terduga di update_calendar_details: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Terjadi kesalahan internal.")

@router.delete(
    "/{calendar_id}", 
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Hapus Kalender"
)
async def delete_a_calendar(
    access_info: CalendarEditorAccessDep, # Keamanan: Cek 'editor'/'owner'
    service: CalendarServiceDep
):
    """
    Menghapus kalender secara permanen.
    
    Fitur:
    Semua 'Subscriptions', 'Schedules', dan 'Instances' terkait
    akan dihapus oleh 'ON DELETE CASCADE' di database.
    
    Keamanan:
    Hanya 'owner' atau 'editor' (sesuai 'get_calendar_editor_access').
    (Kita mungkin perlu memperketat ini HANYA untuk 'owner' di dependency).
    """
    calendar_id = access_info["calendar"]["calendar_id"]
    
    try:
        await service.delete_calendar(calendar_id)
        return # Mengembalikan 204 No Content

    except NotFoundError as e:
        logger.warning(f"Gagal hapus kalender (404): {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Gagal hapus kalender (500): {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Error tidak terduga di delete_a_calendar: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Terjadi kesalahan internal.")