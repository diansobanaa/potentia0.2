# File: backend/api/v1/endpoints/canvases.py
# (FINAL - Menggabungkan 8 endpoint AJAX dan 3 endpoint HARD fallback)

import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, Response
from typing import List, Dict, Any, Optional
from uuid import UUID

# Impor model Pydantic
from app.models.canvas import (
    CanvasCreate, 
    CanvasUpdate, 
    CanvasResponse, 
    CanvasListResponse,
    CanvasMemberInvite
) #
from app.models.block import Block, BlockOperationPayload #
from app.models.workspace import MemberRole #

# Impor dependencies keamanan
from app.core.dependencies import (
    CanvasAccessDep, 
    CanvasAdminAccessDep,
    AuthInfoDep,
    CanvasListServiceDep,
    CanvasSyncManagerDep # Dependency baru untuk H2, H3
) #

# Impor service yang sudah direfaktor
from app.services.canvas.list_service import CanvasListService
from app.services.canvas.sync_manager import CanvasSyncManager
from app.services.redis_rate_limiter import rate_limiter #

# Impor query (untuk A3 dan A8)
from app.db.queries.canvas import block_queries, canvas_member_queries
from app.db.supabase_client import get_supabase_admin_async_client

# Impor router anggota
from . import canvas_members #

logger = logging.getLogger(__name__)

# Prefix "/canvas" didefinisikan di sini
router = APIRouter(
    prefix="/canvas",
    tags=["canvas"]
)

# --- Endpoint A5: Create new canvas ---
#
@router.post(
    "/", 
    response_model=CanvasResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Buat Canvas Baru"
)
async def create_new_canvas(
    payload: CanvasCreate, #
    service: CanvasListServiceDep
):
    """
    Membuat canvas baru (pribadi atau milik workspace).
    
    INPUT: CanvasCreate (title, icon, workspace_id, metadata).
    OUTPUT: CanvasResponse (Objek canvas yang baru dibuat).
    """
    try:
        new_canvas = await service.create_new_canvas(payload)
        return CanvasResponse.model_validate(new_canvas)
    except Exception as e:
        logger.error(f"Gagal membuat canvas: {e}", exc_info=True)
        # TODO: Cek error spesifik (misal, PermissionError)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

# --- Endpoint A4: List user canvases ---
#
@router.get(
    "/", 
    response_model=List[CanvasListResponse],
    summary="List Canvas Pengguna"
)
async def get_my_canvases(
    service: CanvasListServiceDep,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    Mengambil daftar semua canvas yang dapat diakses oleh pengguna
    (pribadi, di-share, atau via workspace).
    """
    try:
        canvases = await service.get_user_canvases(limit=limit, offset=offset)
        return [CanvasListResponse.model_validate(c) for c in canvases]
    except Exception as e:
        logger.error(f"Gagal mengambil daftar canvas: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Gagal mengambil daftar canvas.")

# --- Endpoint A1: Get Detail Canvas ---
#
@router.get(
    "/{canvas_id}", 
    response_model=CanvasResponse,
    summary="Get Detail Canvas"
)
async def get_canvas_details(
    access_info: CanvasAccessDep # Keamanan: Cek 'read'
):
    """
    Mengambil detail sebuah canvas.
    (Endpoint ini bisa dikembangkan untuk A1/A4 Hybrid Snapshot)
    """
    return CanvasResponse.model_validate(access_info["canvas"])

# --- Endpoint A6: Update title, settings ---
#
@router.patch(
    "/{canvas_id}", 
    response_model=CanvasResponse,
    summary="Update Canvas"
)
async def update_canvas_details(
    payload: CanvasUpdate, #
    access_info: CanvasAdminAccessDep, # Keamanan: Cek 'admin'
    service: CanvasListServiceDep
):
    """
    Memperbarui detail canvas (judul, ikon, arsip, metadata).
    Hanya 'owner' atau 'admin' yang dapat melakukan ini.
    """
    canvas_id = access_info["canvas"]["canvas_id"]
    try:
        updated_canvas = await service.update_canvas(canvas_id, payload)
        return CanvasResponse.model_validate(updated_canvas)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Gagal update canvas {canvas_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Gagal memperbarui canvas.")

# --- Endpoint A7: Soft delete ---
#
@router.delete(
    "/{canvas_id}", 
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Hapus (Arsipkan) Canvas"
)
async def delete_canvas(
    access_info: CanvasAdminAccessDep, # Keamanan: Cek 'admin'
    service: CanvasListServiceDep
):
    """
    Menghapus (mengarsipkan) canvas.
    Hanya 'owner' atau 'admin' yang dapat melakukan ini.
    
    CATATAN: Ini meng-patch 'is_archived=true', bukan DELETE permanen.
    """
    canvas_id = access_info["canvas"]["canvas_id"]
    archive_payload = CanvasUpdate(is_archived=True)
    try:
        await service.update_canvas(canvas_id, archive_payload)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        logger.error(f"Gagal mengarsipkan canvas {canvas_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Gagal mengarsipkan canvas.")

# --- Endpoint A2: Paginated blocks ---
#
@router.get(
    "/{canvas_id}/blocks", 
    response_model=List[Block],
    summary="List Blocks di Canvas"
)
async def get_canvas_blocks(
    access_info: CanvasAccessDep, # Keamanan: Cek 'read'
    service: CanvasListServiceDep,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """
    Mengambil daftar block di dalam canvas, dengan paginasi.
    """
    canvas_id = access_info["canvas"]["canvas_id"]
    try:
        blocks = await service.get_canvas_blocks(canvas_id, limit, offset)
        return [Block.model_validate(b) for b in blocks]
    except Exception as e:
        logger.error(f"Gagal mengambil block untuk canvas {canvas_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Gagal mengambil blocks.")

# --- Endpoint H2: Fallback AJAX mutate ---
#
@router.post(
    "/{canvas_id}/mutate",
    summary="Fallback AJAX Mutate",
    response_model=Dict[str, Any]
)
async def http_fallback_mutate(
    payload: BlockOperationPayload, #
    access_info: CanvasAccessDep,
    sync_manager: CanvasSyncManagerDep
):
    """
    Fallback HTTP untuk mutasi (jika WebSocket gagal).
    Blueprint: H2
    """
    role = access_info.get("role")
    if role not in ["owner", "admin", "editor", MemberRole.admin.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Izin tulis diperlukan untuk mutasi."
        )
    
    canvas_id = access_info["canvas"]["canvas_id"]
    user_id = access_info["user"].id
    
    try:
        result = await sync_manager.handle_block_mutation(
            canvas_id, user_id, payload.model_dump()
        )
        
        if result.get("status") == "success":
            return result
        elif result.get("status") == "conflict":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=result
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Mutasi gagal")
            )
            
    except Exception as e:
        logger.error(f"HTTP Mutate gagal: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# --- Endpoint H3: Fallback AJAX presence ---
#
@router.post(
    "/{canvas_id}/presence",
    summary="Fallback AJAX Presence",
    status_code=status.HTTP_200_OK
)
async def http_fallback_presence(
    access_info: CanvasAccessDep,
    sync_manager: CanvasSyncManagerDep,
    payload: Dict[str, Any] = Body(...)
):
    """
    Fallback HTTP untuk update presence (cursor/typing).
    Blueprint: H3
    """
    canvas_id = access_info["canvas"]["canvas_id"]
    user_id = access_info["user"].id
    
    try:
        await sync_manager.handle_presence_update(canvas_id, user_id, payload)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"HTTP Presence gagal: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# --- Endpoint H6: Manual leave ---
#
@router.post(
    "/{canvas_id}/leave",
    summary="Manual Leave Presence",
    status_code=status.HTTP_204_NO_CONTENT
)
async def http_manual_leave(
    access_info: CanvasAccessDep,
    sync_manager: CanvasSyncManagerDep
):
    """
    Memberi tahu server bahwa user meninggalkan canvas (HTTP).
    Blueprint: H6
    """
    canvas_id = access_info["canvas"]["canvas_id"]
    user_id = access_info["user"].id
    
    try:
        await rate_limiter.remove_active_user(user_id, canvas_id) #
        await sync_manager.broadcast_presence_update(
            canvas_id, user_id, {"status": "offline"}
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        logger.error(f"HTTP Leave gagal: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# --- Endpoint A3: Get single block ---
#
@router.get(
    "/{canvas_id}/blocks/{block_id}", 
    response_model=Block,
    summary="Get Single Block"
)
async def get_single_block(
    block_id: UUID,
    access_info: CanvasAccessDep # Keamanan: Cek 'read'
):
    """
    Mengambil data satu block spesifik.
    Blueprint: A3
    """
    try:
        admin_client = await get_supabase_admin_async_client()
        block = await block_queries.get_block_by_id_rpc(admin_client, block_id)
        
        if not block:
            raise HTTPException(status_code=404, detail="Block not found")
        
        if str(block.get("canvas_id")) != str(access_info["canvas"]["canvas_id"]):
            raise HTTPException(status_code=403, detail="Block does not belong to this canvas")
            
        return Block.model_validate(block)
    except Exception as e:
        logger.error(f"Gagal mengambil single block {block_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Gagal mengambil block.")

# --- Endpoint A8: Cek akses ---
#
@router.get(
    "/{canvas_id}/permissions", 
    response_model=Dict[str, Any],
    summary="Get Canvas Permissions"
)
async def get_canvas_permissions(
    access_info: CanvasAccessDep # Keamanan: Cek 'read'
):
    """
    Mendapatkan izin akses user di canvas dan daftar anggota.
    Blueprint: A8
    """
    role = access_info.get("role")
    can_write = role in ["owner", "admin", "editor", MemberRole.admin.value]
    
    try:
        members = await canvas_member_queries.list_canvas_members(
            authed_client=access_info["client"],
            canvas_id=access_info["canvas"]["canvas_id"]
        )
        
        return {
            "can_write": can_write,
            "role": role,
            "users": members
        }
    except Exception as e:
        logger.error(f"Gagal mengambil permissions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Gagal mengambil data izin.")


# --- Menyertakan router anggota ---
# Ini akan membuat endpoint menjadi:
# GET /canvas/{canvas_id}/members/
# POST /canvas/{canvas_id}/members/
#
router.include_router(
    canvas_members.router, 
    prefix="/{canvas_id}/members"
)