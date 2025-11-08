# File: backend/app/db/queries/canvas/canvas_member_queries.py
# (Diperbarui untuk AsyncClient native)

import logging
import asyncio
from uuid import UUID
from typing import List, Dict, Any, Optional
# --- PERBAIKAN: Impor AsyncClient ---
from supabase.client import AsyncClient
from postgrest import APIResponse
from postgrest.exceptions import APIError

from app.core.exceptions import DatabaseError, NotFoundError
from app.models.canvas import CanvasRole
from app.models.user import User
from app.models.workspace import MemberRole

logger = logging.getLogger(__name__)

async def add_canvas_member(
    authed_client: AsyncClient, # <-- Tipe diubah
    canvas_id: UUID,
    user_id: UUID,
    role: CanvasRole
) -> Dict[str, Any]:
    """
    (Async Native) Menambahkan (atau memperbarui) pengguna ke canvas.
    """
    payload = {
        "canvas_id": str(canvas_id),
        "user_id": str(user_id),
        "role": role.value
    }
    
    try:
        # --- PERBAIKAN: Hapus 'to_thread' / 'sync_db_call', gunakan 'await' ---
        response: APIResponse = await (
            authed_client.table("CanvasAccess")
            .upsert(
                payload, 
                on_conflict="canvas_id, user_id",
                returning="representation"
            )
            .execute()
        )
        
        if not response.data or len(response.data) == 0:
            logger.error(f"Gagal upsert anggota {user_id} ke {canvas_id} (data tidak dikembalikan).")
            raise DatabaseError("add_canvas_member_async", "Gagal menambahkan anggota, tidak ada data dikembalikan.")
        
        return response.data[0]
        
    except Exception as e:
        logger.error(f"Error saat add_canvas_member (async) {user_id} ke {canvas_id}: {e}", exc_info=True)
        if "foreign key constraint" in str(e) and "Users" in str(e):
             raise NotFoundError(f"Pengguna dengan ID {user_id} tidak ditemukan.")
        if isinstance(e, (DatabaseError, NotFoundError)):
            raise 
        raise DatabaseError("add_canvas_member_async", f"Error tidak terduka: {str(e)}")

async def list_canvas_members(
    authed_client: AsyncClient, # <-- Tipe diubah
    canvas_id: UUID
) -> List[Dict[str, Any]]:
    """
    (Async Native) Mengambil daftar gabungan anggota canvas via RPC.
    """
    try:
        rpc_function = "get_canvas_members_detailed"
        params = {"p_canvas_id": str(canvas_id)}
        
        # --- PERBAIKAN: Hapus 'to_thread' / 'sync_db_call', gunakan 'await' ---
        response: APIResponse = await (
            authed_client.rpc(rpc_function, params)
            .execute()
        )
        
        if response is None:
             logger.warning(f"RPC {rpc_function} mengembalikan None (canvas: {canvas_id})")
             return []
        if not response.data:
            logger.info(f"RPC {rpc_function} tidak menemukan anggota untuk canvas: {canvas_id}")
            return []
            
        formatted_list = []
        for item in response.data:
            formatted_list.append({
                "role": item.get("role"),
                "user": item.get("user_details") 
            })
        
        return formatted_list
        
    except APIError as e:
         if "PGRST202" in str(e.message): # 'Could not find the function'
            logger.critical(f"FATAL: Fungsi RPC '{rpc_function}' tidak ditemukan.")
            raise DatabaseError("RPC_not_found", "Fungsi database untuk mengambil anggota tidak ditemukan.")
         logger.error(f"APIError saat list_canvas_members (async) {canvas_id}: {e}", exc_info=True)
         raise DatabaseError("list_canvas_members_async", str(e))
    except Exception as e:
        logger.error(f"Error saat list_canvas_members (async) {canvas_id}: {e}", exc_info=True)
        raise DatabaseError("list_canvas_members_async", f"Error tidak terduka: {str(e)}")