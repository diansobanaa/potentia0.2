# File: backend/app/api/v1/endpoints/calendar_subscriptions.py
# (File Baru - TODO-API-4)

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from uuid import UUID

# Impor Model Pydantic
from app.models.schedule import SubscriptionCreate
# (Kita akan buat model respons yang lebih baik nanti)

# Impor Dependencies Keamanan
from app.core.dependencies import (
    CalendarAccessDep,       # Untuk GET (Viewer bisa lihat)
    CalendarEditorAccessDep, # Untuk POST/DELETE (Hanya Editor/Owner)
    SubscriptionServiceDep
)
# Impor Exceptions
from app.core.exceptions import DatabaseError, NotFoundError

logger = logging.getLogger(__name__)

# Definisikan router baru
# Prefix diatur di api.py, tapi kita tambahkan di sini
# untuk kejelasan, dan kita akan hapus dari api.py
router = APIRouter(
    prefix="/calendars/{calendar_id}/subscriptions",
    tags=["calendars"] # Grupkan dengan 'calendars'
)

# =======================================================================
# === ENDPOINT RESOURCE: SUBSCRIPTIONS ===
# =======================================================================

@router.post(
    "/", 
    response_model=Dict[str, Any], # TODO: Buat response model
    status_code=status.HTTP_201_CREATED,
    summary="Undang/Tambah Anggota ke Kalender"
)
async def add_subscription_to_calendar(
    calendar_id: UUID, # Diambil dari path prefix
    payload: SubscriptionCreate,
    access_info: CalendarEditorAccessDep, # Keamanan: Cek 'editor'/'owner'
    service: SubscriptionServiceDep
):
    """
    Menambahkan pengguna baru (via User ID) sebagai subscriber
    ke kalender ini.
    
    Keamanan:
    Hanya 'owner' atau 'editor' dari kalender yang dapat mengundang.
    """
    try:
        new_subscription = await service.create_new_subscription(
            calendar_id, payload
        )
        return new_subscription
        
    except DatabaseError as e:
        logger.error(f"Gagal menambah subscription (500) ke kalender {calendar_id}: {e}", exc_info=True)
        if "invite_conflict" in str(e):
             raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, 
                detail="Pengguna sudah berlangganan ke kalender ini."
            )
        if "owner_demote_prevented" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tidak dapat mengubah role 'owner'."
            )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Error tidak terduga di add_subscription_to_calendar: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Terjadi kesalahan internal.")


@router.get(
    "/", 
    response_model=List[Dict[str, Any]], # TODO: Buat response model
    summary="List Anggota (Subscriber) Kalender"
)
async def get_subscriptions_for_calendar(
    calendar_id: UUID, # Diambil dari path prefix
    access_info: CalendarAccessDep, # Keamanan: Cek 'viewer'
    service: SubscriptionServiceDep
):
    """
    Mengambil daftar semua pengguna yang berlangganan
    ke kalender ini.
    
    Keamanan:
    Hanya pengguna yang sudah memiliki akses (minimal 'viewer')
    yang dapat melihat daftar anggota.
    """
    try:
        subscriptions = await service.get_calendar_subscriptions(calendar_id)
        # TODO: Parsing ini ke response model yang bersih
        return subscriptions
        
    except Exception as e:
        logger.error(f"Gagal mengambil daftar subscription: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Terjadi kesalahan internal.")


# --- Endpoint DELETE (Perlu router terpisah) ---
# Kita perlu router baru karena path-nya tidak mengandung
# /calendars/{calendar_id}

subscription_delete_router = APIRouter(
    prefix="/subscriptions",
    tags=["calendars"]
)

@subscription_delete_router.delete(
    "/{subscription_id}", 
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Hapus Anggota (Unsubscribe)"
)
async def delete_a_subscription(
    subscription_id: UUID,
    service: SubscriptionServiceDep
    # TODO: Keamanan untuk endpoint ini kompleks.
    # Siapa yang boleh menghapus?
    # 1. Pengguna itu sendiri (self-unsubscribe)
    # 2. Admin/Owner kalender (kick)
    # Ini memerlukan dependency keamanan kustom yang
    # mengambil subscription DAN role pengguna di kalender.
):
    """
    Menghapus anggota dari kalender (Unsubscribe atau Kick).
    
    Keamanan (Sederhana - TODO: Perbaiki):
    Saat ini, hanya bergantung pada RLS.
    Harusnya: Cek apakah user = subscription.user_id ATAU
    cek apakah user adalah 'editor'/'owner' dari kalender.
    """
    
    try:
        await service.delete_subscription(subscription_id)
        return # Mengembalikan 204 No Content

    except NotFoundError as e:
        logger.warning(f"Gagal hapus subscription (404): {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Gagal hapus subscription (500): {e}", exc_info=True)
        # TODO: Tangani error 'owner_delete_prevented'
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Error tidak terduga di delete_a_subscription: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Terjadi kesalahan internal.")