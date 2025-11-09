# File: backend/app/api/v1/endpoints/canvases.py

from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional # <-- [DITAMBAHKAN] Optional
from uuid import UUID
import logging 

from app.models.canvas import (
    Canvas, CanvasCreate, PaginatedCanvasListResponse,
    CanvasMetaUpdate  
)
from app.models.user import User

from app.core.dependencies import (
    get_current_user_and_client, 
    get_current_workspace_member,
    AuthInfoDep,
    WorkspaceMemberDep,
    CanvasListServiceDep,
    CanvasAccessDep  
)
from app.db.queries.canvas.canvas_queries import (
    create_canvas, 
    delete_canvas,
    update_canvas_metadata,     
    set_canvas_archived_status  
)
from app.services.canvas_list_service import CanvasListService 

from app.core.exceptions import DatabaseError, NotFoundError

router = APIRouter()
logger = logging.getLogger(__name__)

# --- Endpoint Create (Sudah diperbaiki error handling-nya) ---
@router.post("/workspace/{workspace_id}", response_model=Canvas, status_code=status.HTTP_201_CREATED)
async def create_canvas_in_workspace(
    workspace_id: UUID,
    canvas_data: CanvasCreate,
    member_info: WorkspaceMemberDep 
):
    """
    **Membuat kanvas baru dan mengaitkannya dengan *workspace* yang ditentukan.**
    
    Pengguna pembuat menjadi *owner* kanvas tersebut. 
    
    **Keamanan:** Membutuhkan **keanggotaan aktif** dalam *workspace* yang ditargetkan.
    Mengembalikan objek kanvas yang baru dibuat (201 Created).
    """
    current_user = member_info["user"]
    authed_client = member_info["client"]
    try:
        new_canvas = create_canvas(
            authed_client, canvas_data.title, canvas_data.icon, 
            workspace_id, current_user.id, None
        )
        if not new_canvas:
            logger.error(f"Gagal membuat canvas di workspace {workspace_id} (data tidak dikembalikan).")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Gagal membuat canvas di database (tidak ada data dikembalikan)."
            )
        return new_canvas
    except Exception as e:
        logger.error(f"Error di endpoint create_canvas_in_workspace: {e}", exc_info=True)
        if "check constraint" in str(e) or "foreign key constraint" in str(e):
             raise HTTPException(
                 status_code=status.HTTP_400_BAD_REQUEST, 
                 detail=f"Gagal membuat canvas: {str(e)}"
             )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Terjadi kesalahan internal saat membuat canvas."
        )

@router.post("/personal", response_model=Canvas, status_code=status.HTTP_201_CREATED)
async def create_personal_canvas(
    canvas_data: CanvasCreate,
    auth_info: AuthInfoDep 
):
    """
    Membuat canvas pribadi baru untuk pengguna yang sedang login.
    Error handling sudah ditambahkan.
    """
    current_user = auth_info["user"]
    authed_client = auth_info["client"]
    try:
        new_canvas = create_canvas(
            authed_client, canvas_data.title, canvas_data.icon, 
            None, current_user.id, current_user.id
        )
        if not new_canvas:
            logger.error(f"Gagal membuat canvas personal untuk user {current_user.id} (data tidak dikembalikan).")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Gagal membuat canvas di database (tidak ada data dikembalikan)."
            )
        return new_canvas
    except Exception as e:
        logger.error(f"Error di endpoint create_personal_canvas: {e}", exc_info=True)
        if "check constraint" in str(e) or "foreign key constraint" in str(e):
             raise HTTPException(
                 status_code=status.HTTP_400_BAD_REQUEST, 
                 detail=f"Gagal membuat canvas: {str(e)}"
             )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Terjadi kesalahan internal saat membuat canvas."
        )

# --- Endpoint Read List (Sudah ada) ---
@router.get("/workspace/{workspace_id}", response_model=PaginatedCanvasListResponse)
async def list_canvases_in_workspace(
    workspace_id: UUID,
    member_info: WorkspaceMemberDep,
    canvas_service: CanvasListServiceDep,
    page: int = Query(1, ge=1, description="Nomor halaman, dimulai dari 1"),
    size: int = Query(20, ge=1, le=100, description="Jumlah item per halaman (maks 100)")
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
    auth_info: AuthInfoDep,
    canvas_service: CanvasListServiceDep,
    page: int = Query(1, ge=1, description="Nomor halaman, dimulai dari 1"),
    size: int = Query(20, ge=1, le=100, description="Jumlah item per halaman (maks 100)")
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

# --- [ENDPOINT BARU 1: GET DETAIL] ---
@router.get("/{canvas_id}", response_model=Canvas)
async def get_canvas_details(
    access_info: CanvasAccessDep 
):
    """
    Mengambil detail untuk satu canvas spesifik. Dilindungi oleh CanvasAccessDep.
    
    INPUT: Path (canvas_id: UUID).
    OUTPUT: Canvas (detail Canvas, metadata, status arsip).
    
    KAPAN DIGUNAKAN: Dipanggil saat memuat Canvas Editor untuk memuat metadata Canvas.
    """
    return access_info["canvas"]

@router.patch("/{canvas_id}/meta", response_model=Canvas)
async def update_canvas_metadata_endpoint(
    payload: CanvasMetaUpdate,
    access_info: CanvasAccessDep 
):
    """
    Memperbarui metadata canvas (judul atau ikon).
    Keamanan: 'CanvasAccessDep' memastikan hanya pengguna dengan
    akses (Personal, Workspace, atau Invite) yang dapat memanggil endpoint ini.
    """
    canvas_id = access_info["canvas"]["canvas_id"]
    authed_client = access_info["client"]
    
    # Ambil data untuk di-update, buang nilai None
    update_data = payload.model_dump(exclude_unset=True)
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tidak ada data untuk diperbarui (judul atau ikon)."
        )

    try:
        updated_canvas = await update_canvas_metadata(
            authed_client=authed_client,
            canvas_id=canvas_id,
            update_data=update_data
        )
        return updated_canvas
        
    except NotFoundError as e:
        # Fallback jika data tidak ada di DB
        logger.warning(f"Gagal update meta (404) untuk canvas {canvas_id}: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DatabaseError as e:
        # Fallback jika DB error
        logger.error(f"Gagal update meta (500) untuk canvas {canvas_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Error tidak terduga di update_canvas_metadata_endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Terjadi kesalahan internal.")

# --- [ENDPOINT BARU 2: Archive (Perbaikan Tes 2)] ---
@router.post("/{canvas_id}/archive", response_model=Canvas)
async def archive_canvas(
    access_info: CanvasAccessDep
):
    """
    **Melakukan Soft Delete pada kanvas dengan mengatur status `is_archived` menjadi `True`.**

    Kanvas yang diarsip akan hilang dari daftar default dan hanya bisa dilihat di tampilan arsip.
    
    **Keamanan:** Membutuhkan akses **Editor** atau **Owner** ke kanvas.
    """
    canvas_id = access_info["canvas"]["canvas_id"]
    authed_client = access_info["client"]
    
    try:
        updated_canvas = await set_canvas_archived_status(
            authed_client=authed_client,
            canvas_id=canvas_id,
            is_archived=True
        )
        return updated_canvas
        
    except NotFoundError as e:
        # Fallback jika data tidak ada di DB
        logger.warning(f"Gagal arsip (404) untuk canvas {canvas_id}: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DatabaseError as e:
        # Fallback jika DB error
        logger.error(f"Gagal arsip (500) untuk canvas {canvas_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Error tidak terduga di archive_canvas: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Terjadi kesalahan internal.")

# --- [ENDPOINT BARU 3: Restore (Perbaikan Tes 2)] ---
@router.post("/{canvas_id}/restore", response_model=Canvas)
async def restore_canvas(
    access_info: CanvasAccessDep
):
    """
    **Memulihkan kanvas dari status terarsip dengan mengatur `is_archived` menjadi `False`.**

    Kanvas yang dipulihkan akan kembali muncul dalam daftar normal.

    **Keamanan:** Membutuhkan akses **Editor** atau **Owner** ke kanvas.
    """
    canvas_id = access_info["canvas"]["canvas_id"]
    authed_client = access_info["client"]

    try:
        updated_canvas = await set_canvas_archived_status(
            authed_client=authed_client,
            canvas_id=canvas_id,
            is_archived=False
        )
        return updated_canvas
        
    except NotFoundError as e:
        # Fallback jika data tidak ada di DB
        logger.warning(f"Gagal restore (404) untuk canvas {canvas_id}: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DatabaseError as e:
        # Fallback jika DB error
        logger.error(f"Gagal restore (500) untuk canvas {canvas_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Error tidak terduga di restore_canvas: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Terjadi kesalahan internal.")

# --- [ENDPOINT DELETE (Sudah aman dari crash 404)] ---
@router.delete("/{canvas_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_canvas_permanently(
    access_info: CanvasAccessDep
):
    """
    Menghapus canvas secara permanen (Hard Delete).
    PERINGATAN: Akan gagal (409 Conflict) jika canvas masih memiliki blocks.
    """
    canvas_id = access_info["canvas"]["canvas_id"]
    authed_client = access_info["client"]

    try:
        await delete_canvas(
            authed_client=authed_client,
            canvas_id=canvas_id
        )
        return
        
    except NotFoundError as e:
        # Fallback jika canvas tidak ada (Perbaikan Tes 3)
        logger.warning(f"Gagal delete (404) untuk canvas {canvas_id}: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Gagal delete (500/409) untuk canvas {canvas_id}: {e}", exc_info=True)
        if "delete_canvas_fk" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, 
                detail="Canvas tidak dapat dihapus karena masih berisi data (blocks)."
            )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Error tidak terduga di delete_canvas_permanently: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Terjadi kesalahan internal.")