# File: backend/app/api/v1/endpoints/canvas_members.py

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from uuid import UUID

# Impor model Pydantic yang kita buat
from app.models.canvas import CanvasMemberInvite
# Impor model Pydantic untuk respons
from app.models.user import User
from app.models.canvas import CanvasRole

# Impor dependencies keamanan
from app.core.dependencies import CanvasAccessDep, CanvasAdminAccessDep

# Impor fungsi query yang baru kita buat
from app.db.queries.canvas.canvas_member_queries import (
    add_canvas_member, 
    list_canvas_members
)
# Impor exceptions
from app.core.exceptions import DatabaseError, NotFoundError

logger = logging.getLogger(__name__)

# Kita gunakan 'tags' yang sama dengan 'canvases' agar terkelompok
router = APIRouter(tags=["canvases"])

# --- [ENDPOINT BARU 1: LIST MEMBERS] ---
@router.get(
    "/", 
    response_model=List[Dict[str, Any]], # Kita akan kembalikan list dict
    summary="List Canvas Members"
)
async def get_members_in_canvas(
    access_info: CanvasAccessDep # <- Keamanan: Semua yang punya akses bisa melihat
):
    """
    Mengambil daftar semua anggota yang memiliki akses langsung 
    ke canvas ini (via tabel CanvasAccess).
    
    Keamanan:
    Hanya pengguna yang sudah memiliki akses (Owner, Member, atau Invited) 
    yang dapat melihat daftar anggota.
    """
    canvas_id = access_info["canvas"]["canvas_id"]
    authed_client = access_info["client"]

    try:
        members = await list_canvas_members(
            authed_client=authed_client,
            canvas_id=canvas_id
        )
        return members
        
    except DatabaseError as e:
        logger.error(f"Gagal list members (500) untuk canvas {canvas_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Error tidak terduga di get_members_in_canvas: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Terjadi kesalahan internal.")


# --- [ENDPOINT BARU 2: INVITE MEMBER] ---
@router.post(
    "/", 
    response_model=Dict[str, Any], # Kita kembalikan data member yang baru ditambahkan
    status_code=status.HTTP_201_CREATED,
    summary="Invite/Add Member to Canvas"
)
async def invite_member_to_canvas(
    payload: CanvasMemberInvite,
    access_info: CanvasAdminAccessDep # <- Keamanan: HANYA ADMIN/OWNER
):
    """
    Mengundang (atau menambahkan) pengguna baru ke canvas.
    
    Keamanan:
    Hanya 'owner' dari canvas personal atau 'admin' dari workspace 
    yang dapat mengundang anggota baru.
    
    Logika:
    Saat ini, endpoint ini HANYA mendukung invite via 'user_id'. 
    Logika invite via 'email' (membuat token di tabel CanvasInvitations) 
    perlu ditambahkan di masa depan.
    """
    canvas_id = access_info["canvas"]["canvas_id"]
    authed_client = access_info["client"]

    # Validasi payload (kita hanya implementasi 'user_id' dulu)
    if not payload.user_id:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Invite via email belum diimplementasikan. Harap sediakan 'user_id'."
        )
        
    # Cek agar pengguna tidak mengundang diri sendiri
    current_user_id = access_info["user"].id
    if payload.user_id == current_user_id:
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tidak dapat mengundang diri sendiri."
        )

    try:
        new_member_access = await add_canvas_member(
            authed_client=authed_client,
            canvas_id=canvas_id,
            user_id=payload.user_id,
            role=payload.role
        )
        return new_member_access
        
    except NotFoundError as e:
        # Ini terjadi jika 'user_id' yang diundang tidak ada
        logger.warning(f"Gagal invite (404) ke canvas {canvas_id}: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Gagal invite (500) ke canvas {canvas_id}: {e}", exc_info=True)
        if "already exists" in str(e) or "unique constraint" in str(e):
             raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, 
                detail="Pengguna sudah menjadi anggota."
            )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Error tidak terduga di invite_member_to_canvas: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Terjadi kesalahan internal.")