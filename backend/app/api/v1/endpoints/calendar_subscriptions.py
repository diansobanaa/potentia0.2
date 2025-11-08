# File: backend/app/api/v1/endpoints/calendar_subscriptions.py
# (Diperbarui dengan Dependency Keamanan)

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from uuid import UUID

from app.models.schedule import SubscriptionCreate
from app.core.dependencies import (
    CalendarAccessDep,
    CalendarEditorAccessDep,
    SubscriptionServiceDep,
    get_subscription_delete_access 
)
from app.core.exceptions import DatabaseError, NotFoundError

logger = logging.getLogger(__name__)

# (Router 'router' tetap sama)
router = APIRouter(
    prefix="/calendars/{calendar_id}/subscriptions",
    tags=["calendars"] 
)
# (Endpoint POST dan GET tetap sama)
@router.post(
    "/", 
    response_model=Dict[str, Any], 
    status_code=status.HTTP_201_CREATED,
    summary="Undang/Tambah Anggota ke Kalender"
)
async def add_subscription_to_calendar(
    calendar_id: UUID, 
    payload: SubscriptionCreate,
    access_info: CalendarEditorAccessDep, 
    service: SubscriptionServiceDep
):
    # (...logika tidak berubah...)
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
    response_model=List[Dict[str, Any]], 
    summary="List Anggota (Subscriber) Kalender"
)
async def get_subscriptions_for_calendar(
    calendar_id: UUID, 
    access_info: CalendarAccessDep, 
    service: SubscriptionServiceDep
):
    # (...logika tidak berubah...)
    try:
        subscriptions = await service.get_calendar_subscriptions(calendar_id)
        
        return subscriptions
    
    except Exception as e:
        logger.error(f"Gagal mengambil daftar subscription: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Terjadi kesalahan internal.")


# --- Endpoint DELETE (Perlu router terpisah) ---
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
    service: SubscriptionServiceDep,                                         
    access_info: Dict[str, Any] = Depends(get_subscription_delete_access),  
):
    """
    Menghapus anggota dari kalender (Unsubscribe atau Kick).
    
    Keamanan:
    Sekarang dilindungi oleh dependency 'get_subscription_delete_access'.
    Hanya pengguna ybs atau admin/owner kalender yang bisa menghapus.
    """
    
    # Ambil data dari dependency yang sudah divalidasi
    subscription_id = access_info["subscription"]["subscription_id"]
    subscriber_to_delete = access_info["subscription"] # Data lengkap
    
    try:
        # Panggil service, sekarang dengan data subscriber
        await service.delete_subscription(subscription_id, subscriber_to_delete)
        return # Mengembalikan 204 No Content

    except NotFoundError as e:
        logger.warning(f"Gagal hapus subscription (404): {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Gagal hapus subscription (500): {e}", exc_info=True)
        # Tangani error pencegahan penghapusan 'owner' dari service
        if "owner_delete_prevented" in str(e):
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Pemilik (Owner) kalender tidak dapat dihapus."
            )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Error tidak terduga di delete_a_subscription: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Terjadi kesalahan internal.")