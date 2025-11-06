from fastapi import APIRouter, Depends, HTTPException, status, Query # <-- Tambahkan Query
from typing import List
from uuid import UUID

# [DIUBAH] Impor model paginasi
from app.models.workspace import (
    Workspace, WorkspaceCreate, WorkspaceUpdate, MemberRole,
    PaginatedWorkspaceListResponse
)
from app.models.user import User
from app.core.dependencies import (
    get_current_user_and_client, 
    AuthInfoDep, 
    WorkspaceMemberDep, 
    WorkspaceServiceDep 
)
from app.services.workspace.workspace_service import WorkspaceService
from app.core.exceptions import DatabaseError, NotFoundError
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/", response_model=Workspace, status_code=201)
async def create_workspace(
    # ... (endpoint ini tetap sama) ...
    workspace_data: WorkspaceCreate,
    service: WorkspaceServiceDep
):
    try:
        new_workspace = await service.create_new_workspace(workspace_data) 
        return new_workspace
    except Exception as e:
        logger.error(f"Error di create_workspace: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Gagal membuat workspace.")

# --- [ENDPOINT INI DIPERBARUI UNTUK PAGINASI] ---
@router.get("/", response_model=PaginatedWorkspaceListResponse)
async def list_my_workspaces(
    service: WorkspaceServiceDep,
    # [DIUBAH] Tambahkan parameter Query
    page: int = Query(1, ge=1, description="Nomor halaman, dimulai dari 1"),
    size: int = Query(20, ge=1, le=100, description="Jumlah item per halaman (maks 100)")
):
    """Mengambil daftar semua workspace di mana pengguna adalah anggota (paginasi)."""
    try:
        # [DIUBAH] Memanggil fungsi service paginasi yang baru
        return await service.get_paginated_user_workspaces(page=page, size=size)
    except Exception as e:
        logger.error(f"Error di list_my_workspaces: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Gagal mengambil daftar workspace.")
# --- [AKHIR PERUBAHAN] ---

@router.get("/{workspace_id}", response_model=Workspace)
async def get_workspace(
    # ... (endpoint ini tetap sama) ...
    workspace_id: UUID,
    member_info: WorkspaceMemberDep,
    service: WorkspaceServiceDep
):
    try:
        return await service.get_workspace_details(workspace_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error di get_workspace: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Gagal mengambil data workspace.")

@router.patch("/{workspace_id}", response_model=Workspace)
async def update_workspace(
    # ... (endpoint ini tetap sama) ...
    workspace_id: UUID,
    payload: WorkspaceUpdate,
    member_info: WorkspaceMemberDep,
    service: WorkspaceServiceDep
):
    try:
        updated_workspace = await service.update_workspace_details(workspace_id, payload)
        return updated_workspace
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error di update_workspace: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Gagal memperbarui workspace.")

@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    # ... (endpoint ini tetap sama) ...
    workspace_id: UUID,
    member_info: WorkspaceMemberDep,
    service: WorkspaceServiceDep
):
    try:
        success = await service.delete_workspace(workspace_id)
        if not success:
            raise NotFoundError("Workspace tidak ditemukan atau Anda bukan pemilik.")
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error di delete_workspace: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Gagal menghapus workspace.")