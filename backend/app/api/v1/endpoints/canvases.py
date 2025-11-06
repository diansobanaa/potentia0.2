from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
from uuid import UUID
import logging # <-- Tambahkan logging

from app.models.canvas import Canvas, CanvasCreate, PaginatedCanvasListResponse 
from app.models.user import User

from app.core.dependencies import (
    get_current_user_and_client, 
    get_current_workspace_member,
    # --- [DIUBAH] Gunakan Alias 'Annotated' ---
    AuthInfoDep,
    WorkspaceMemberDep,
    CanvasListServiceDep 
    # --- AKHIR PERUBAHAN ---
)
from app.db.queries.canvas_queries import create_canvas 
from app.services.canvas_list_service import CanvasListService 

router = APIRouter()
logger = logging.getLogger(__name__) # <-- Tambahkan logger

@router.post("/workspace/{workspace_id}", response_model=Canvas, status_code=201)
async def create_canvas_in_workspace(
    workspace_id: UUID,
    canvas_data: CanvasCreate,
    # [DIUBAH] Gunakan alias 'WorkspaceMemberDep'
    member_info: WorkspaceMemberDep 
):
    """
    Membuat canvas baru di dalam workspace tertentu.
    """
    current_user = member_info["user"]
    authed_client = member_info["client"]

    new_canvas = create_canvas(authed_client, canvas_data.title, canvas_data.icon, workspace_id, current_user.id, None)
    return new_canvas

@router.post("/personal", response_model=Canvas, status_code=201)
async def create_personal_canvas(
    canvas_data: CanvasCreate,
    # [DIUBAH] Gunakan alias 'AuthInfoDep'
    auth_info: AuthInfoDep 
):
    """
    Membuat canvas pribadi baru untuk pengguna yang sedang login.
    """
    current_user = auth_info["user"]
    authed_client = auth_info["client"]

    new_canvas = create_canvas(authed_client, canvas_data.title, canvas_data.icon, None, current_user.id, current_user.id)
    return new_canvas

@router.get("/workspace/{workspace_id}", response_model=PaginatedCanvasListResponse)
async def list_canvases_in_workspace(
    workspace_id: UUID,
    # --- [PERBAIKAN DI SINI] ---
    member_info: WorkspaceMemberDep,
    canvas_service: CanvasListServiceDep, # <-- Hapus '= Depends()'
    page: int = Query(1, ge=1, description="Nomor halaman, dimulai dari 1"),
    size: int = Query(20, ge=1, le=100, description="Jumlah item per halaman (maks 100)")
    # --- AKHIR PERBAIKAN ---
):
    """
    Menampilkan daftar semua canvas yang tidak diarsip 
    di dalam workspace tertentu, DENGAN PAGINATION.
    """
    try:
        return await canvas_service.get_paginated_workspace_canvases(
            workspace_id=workspace_id, page=page, size=size
        )
    except Exception as e:
        logger.error(f"Error di endpoint list_canvases_in_workspace: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Gagal mengambil data canvas workspace.")

@router.get("/personal", response_model=PaginatedCanvasListResponse)
async def list_personal_canvases(
    # --- [PERBAIKAN DI SINI] ---
    auth_info: AuthInfoDep,
    canvas_service: CanvasListServiceDep, # <-- Hapus '= Depends()'
    page: int = Query(1, ge=1, description="Nomor halaman, dimulai dari 1"),
    size: int = Query(20, ge=1, le=100, description="Jumlah item per halaman (maks 100)")
    # --- AKHIR PERBAIKAN ---
):
    """
    Menampilkan daftar semua canvas pribadi 
    milik pengguna yang sedang login, DENGAN PAGINATION.
    """
    try:
        return await canvas_service.get_paginated_personal_canvases(
            page=page, size=size
        )
    except Exception as e:
        logger.error(f"Error di endpoint list_personal_canvases: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Gagal mengambil data canvas pribadi.") 