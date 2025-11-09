# File: backend/app/api/v1/endpoints/views.py
# (File Baru - TODO-API-6)

import logging
import pytz
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Dict, Any
from uuid import UUID
from datetime import datetime

# Impor Model Pydantic
from app.models.schedule import ScheduleInstance
from app.services.calendar.view_service import PaginatedScheduleInstanceResponse

# Impor Dependencies
from app.core.dependencies import (
    AuthInfoDep,
    ViewServiceDep,
    FreeBusyServiceDep # Service yang sudah ada
)
# Impor Exceptions
from app.core.exceptions import DatabaseError

logger = logging.getLogger(__name__)

# Definisikan router baru
router = APIRouter(
    prefix="/view",
    tags=["schedules"] # Kita kelompokkan di tag 'schedules'
)

# =======================================================================
# === ENDPOINT RESOURCE: VIEWS (Tampilan Terpadu) ===
# =======================================================================

@router.get(
    "/schedules", 
    response_model=PaginatedScheduleInstanceResponse,
    summary="Tampilan Kalender (Cepat)"
)
async def get_schedule_view_for_user(
    start: datetime, # FastAPI akan mem-parse string ISO
    end: datetime,   # (misal: 2025-12-01T00:00:00Z)
    service: ViewServiceDep,
    auth_info: AuthInfoDep,
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=500) # Paginasi (Optimasi 4)
):
    """
    Endpoint utama untuk UI Kalender.
    
    Fitur:
    - Sangat cepat: Membaca dari tabel 'ScheduleInstances' (pre-computed).
    - Terpadu: Mengambil acara dari SEMUA kalender yang di-subscribe pengguna.
    - Aman: Otomatis mem-filter berdasarkan 'user_id' yang login.
    
    KAPAN DIGUNAKAN: Saat memuat tampilan bulan/minggu/hari di UI Kalender. Kunci performa aplikasi.
    """
    
    # Fallback: Pastikan 'start' dan 'end' adalah UTC
    if start.tzinfo is None:
        start = start.replace(tzinfo=pytz.UTC)
    if end.tzinfo is None:
        end = end.replace(tzinfo=pytz.UTC)
        
    try:
        paginated_response = await service.get_paginated_schedule_view(
            start_time=start,
            end_time=end,
            page=page,
            size=size
        )
        return paginated_response
        
    except DatabaseError as e:
        logger.error(f"Gagal mengambil /view/schedules: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Error tidak terduga di get_schedule_view_for_user: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Terjadi kesalahan internal.")


@router.get(
    "/freebusy", 
    response_model=Dict[str, List[Dict[str, Any]]],
    summary="Cek Ketersediaan (Free/Busy)"
)
async def get_freebusy_view_for_users(
    service: FreeBusyServiceDep,
    auth_info: AuthInfoDep,
    start: datetime = Query(..., description="Waktu mulai (UTC)"),
    end: datetime = Query(..., description="Waktu selesai (UTC)"),
    user_ids: List[UUID] = Query(..., description="Daftar User ID yang ingin dicek."),
):
    """
    Endpoint skalabel untuk deteksi konflik jadwal.
    
    Fitur:
    - Sangat cepat: Menggunakan 'Redis-first cache'.
    - Fallback: Jika cache kosong, akan mengambil dari 'ScheduleInstances'
      (menggunakan index 'user_id').
    
    Mengembalikan:
    Dict[user_id, List[blok_sibuk]]

    KAPAN DIGUNAKAN: Saat pengguna mencoba membuat rapat dan perlu mengetahui kapan rekan satu timnya sedang sibuk.
    """
    
    # Fallback: Pastikan 'start' dan 'end' adalah UTC
    if start.tzinfo is None:
        start = start.replace(tzinfo=pytz.UTC)
    if end.tzinfo is None:
        end = end.replace(tzinfo=pytz.UTC)
        
    try:
        # Panggil service yang sudah kita buat (TODO-SVC-3)
        freebusy_data = await service.get_freebusy_for_users(
            user_ids=user_ids,
            start_time=start,
            end_time=end
        )
        return freebusy_data
        
    except DatabaseError as e:
        logger.error(f"Gagal mengambil /view/freebusy: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Error tidak terduga di get_freebusy_view_for_users: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Terjadi kesalahan internal.")