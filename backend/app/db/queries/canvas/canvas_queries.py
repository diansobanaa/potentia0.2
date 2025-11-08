# File: backend/app/db/queries/canvas/canvas_queries.py
# (Diperbarui untuk AsyncClient native dan asyncio.gather)

from typing import List, Optional, Tuple, Dict, Any 
from uuid import UUID
# --- PERBAIKAN: Impor AsyncClient ---
from supabase.client import AsyncClient
from postgrest import APIResponse, APIError
import logging
import asyncio 
from app.core.exceptions import DatabaseError, NotFoundError

logger = logging.getLogger(__name__)

async def create_canvas(authed_client: AsyncClient, title: str, icon: str, workspace_id: Optional[UUID], creator_id: UUID, user_id: Optional[UUID]) -> Optional[dict]:
    payload = {"title": title, "icon": icon, "creator_user_id": str(creator_id)}
    if workspace_id: payload["workspace_id"] = str(workspace_id)
    if user_id: payload["user_id"] = str(user_id)
    
    # (Insert sudah benar)
    response = await authed_client.table("Canvas").insert(payload, returning="representation").execute() 
    return response.data[0] if response.data else None

async def update_canvas_metadata(
    authed_client: AsyncClient, 
    canvas_id: UUID, 
    update_data: Dict[str, Any]
) -> Dict[str, Any]:
    try:
        # --- PERBAIKAN: Hapus .single() ---
        response: APIResponse = await (
            authed_client.table("Canvas")
            .update(update_data, returning="representation")
            .eq("canvas_id", str(canvas_id))
            .execute()
        )
        # ---------------------------------
        if not response.data or len(response.data) == 0:
            raise NotFoundError("Canvas tidak ditemukan saat proses update metadata.")
        return response.data[0]
    except Exception as e:
        if isinstance(e, (DatabaseError, NotFoundError)): raise 
        raise DatabaseError("update_canvas_meta_async", f"Error tidak terduka: {str(e)}")
    
async def set_canvas_archived_status(
    authed_client: AsyncClient, 
    canvas_id: UUID, 
    is_archived: bool
) -> Dict[str, Any]:
    update_data = {"is_archived": is_archived}
    try:
        # --- PERBAIKAN: Hapus .single() ---
        response: APIResponse = await (
            authed_client.table("Canvas")
            .update(update_data, returning="representation")
            .eq("canvas_id", str(canvas_id))
            .execute()
        )
        # ---------------------------------
        if not response.data or len(response.data) == 0:
            raise NotFoundError("Canvas tidak ditemukan saat update status arsip.")
        return response.data[0]
    except Exception as e:
        if isinstance(e, (DatabaseError, NotFoundError)): raise 
        raise DatabaseError("set_canvas_archive_async", f"Error tidak terduka: {str(e)}")
    
async def delete_canvas(
    authed_client: AsyncClient, 
    canvas_id: UUID
) -> bool:
    try:
        # --- PERBAIKAN: Hapus .single() ---
        response: APIResponse = await (
            authed_client.table("Canvas")
            .delete(returning="representation")
            .eq("canvas_id", str(canvas_id))
            .execute()
        )
        # ---------------------------------
        success = bool(response.data and len(response.data) > 0)
        if not success:
            raise NotFoundError("Canvas tidak ditemukan untuk dihapus.")
        return True
    except Exception as e:
        if "violates foreign key constraint" in str(e):
            raise DatabaseError("delete_canvas_fk", "Canvas tidak dapat dihapus karena masih memiliki block.")
        if isinstance(e, (DatabaseError, NotFoundError)): raise 
        raise DatabaseError("delete_canvas_async", f"Error tidak terduka: {str(e)}")
    
async def get_canvases_in_workspace_paginated(
    authed_client: AsyncClient, # <-- Tipe diubah
    workspace_id: UUID, 
    offset: int, 
    limit: int
) -> Tuple[List[Dict[str, Any]], int]:
    """
    (Async Native) Mengambil daftar canvas workspace dengan paginasi.
    """
    try:
        # --- PERBAIKAN: Optimasi dengan asyncio.gather ---
        list_task = authed_client.table("Canvas") \
            .select("*") \
            .eq("workspace_id", str(workspace_id)) \
            .eq("is_archived", False) \
            .order("updated_at", desc=True) \
            .range(offset, offset + limit - 1) \
            .execute()

        count_task = authed_client.table("Canvas") \
            .select("canvas_id", count="exact") \
            .eq("workspace_id", str(workspace_id)) \
            .eq("is_archived", False) \
            .execute()
        
        list_response, count_response = await asyncio.gather(list_task, count_task)
        # ---------------------------------------------
        
        data = list_response.data or []
        total = count_response.count or 0
        return data, total
    
    except Exception as e:
        logger.error(f"Error paginating workspace canvases (async) for {workspace_id}: {e}", exc_info=True)
        return [], 0

async def get_user_personal_canvases_paginated(
    authed_client: AsyncClient, # <-- Tipe diubah
    user_id: UUID, 
    offset: int, 
    limit: int
) -> Tuple[List[Dict[str, Any]], int]:
    """
    (Async Native) Mengambil daftar canvas pribadi user dengan paginasi.
    """
    try:
        # --- PERBAIKAN: Optimasi dengan asyncio.gather ---
        list_task = authed_client.table("Canvas") \
            .select("*") \
            .eq("user_id", str(user_id)) \
            .eq("is_archived", False) \
            .order("updated_at", desc=True) \
            .range(offset, offset + limit - 1) \
            .execute()

        count_task = authed_client.table("Canvas") \
            .select("canvas_id", count="exact") \
            .eq("user_id", str(user_id)) \
            .eq("is_archived", False) \
            .execute()
        
        list_response, count_response = await asyncio.gather(list_task, count_task)
        # ---------------------------------------------
        
        data = list_response.data or []
        total = count_response.count or 0
        return data, total
    except Exception as e:
        logger.error(f"Error paginating personal canvases (async) for {user_id}: {e}", exc_info=True)
        return [], 0

async def get_canvas_by_id(
    authed_client: AsyncClient, # <-- Tipe diubah
    canvas_id: UUID
) -> Optional[dict]:
    """
    (Async Native) Mengambil satu data canvas berdasarkan ID-nya.
    """
    try:
        # --- PERBAIKAN: Gunakan 'await' ---
        response: APIResponse = await (
            authed_client.table("Canvas")
            .select("*")
            .eq("canvas_id", str(canvas_id))
            .maybe_single() 
            .execute()
        )
        
        if response is None:
            logger.warning(f"get_canvas_by_id (async): Supabase client mengembalikan 'None' untuk canvas {canvas_id}.")
            return None
        if not response.data:
            logger.info(f"get_canvas_by_id (async): Canvas {canvas_id} tidak ditemukan di DB.")
            return None
            
        return response.data

    except APIError as e:
        logger.error(f"APIError di get_canvas_by_id (async) {canvas_id}: {e.message}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Error umum di get_canvas_by_id (async) {canvas_id}: {e}", exc_info=True)
        return None

async def check_user_canvas_access(
    authed_client: AsyncClient, # <-- Tipe diubah
    canvas_id: UUID, 
    user_id: UUID
) -> Optional[Dict[str, Any]]:
    """
    (Async Native) Memeriksa 'CanvasAccess' (logika invite).
    """
    try:
        # --- PERBAIKAN: Hapus 'to_thread', gunakan 'await' ---
        response: APIResponse = await (
            authed_client.table("CanvasAccess")
            .select("role")
            .eq("canvas_id", str(canvas_id))
            .eq("user_id", str(user_id))
            .limit(1)
            .maybe_single()
            .execute()
        )
        return response.data if response.data else None
    except Exception as e:
        logger.error(f"Error saat check_user_canvas_access (async): {e}", exc_info=True)
        return None
            
async def get_blocks_in_canvas(
    authed_client: AsyncClient, # <-- Tipe diubah
    canvas_id: UUID
) -> List[dict]:
    # --- PERBAIKAN: Gunakan 'await' ---
    response = await authed_client.table("Blocks") \
        .select("*") \
        .eq("canvas_id", str(canvas_id)) \
        .order("y_order") \
        .execute()
    return response.data if response.data else []

async def update_block(authed_client: AsyncClient, block_id: UUID, update_data: dict) -> Optional[dict]:
    # --- PERBAIKAN: Hapus .single() ---
    response = await authed_client.table("Blocks") \
        .update(update_data, returning="representation") \
        .eq("block_id", str(block_id)) \
        .execute()
    # ---------------------------------
    return response.data[0] if response.data else None

async def delete_block(authed_client: AsyncClient, block_id: UUID) -> bool:
    # --- PERBAIKAN: Hapus .single() ---
    response = await authed_client.table("Blocks") \
        .delete(returning="representation") \
        .eq("block_id", str(block_id)) \
        .execute()
    # ---------------------------------
    return len(response.data) > 0

async def get_all_accessible_canvases(authed_client: AsyncClient, user_id: UUID) -> List[dict]:
    personal_canvases_task = get_user_personal_canvases_paginated(authed_client, user_id, 0, 1000)
    workspace_memberships_task = authed_client.table("WorkspaceMembers").select("workspace_id").eq("user_id", str(user_id)).execute()
    (personal_canvases_data, workspace_memberships) = await asyncio.gather(personal_canvases_task, workspace_memberships_task)
    personal_canvases = personal_canvases_data[0]
    workspace_ids = [m['workspace_id'] for m in workspace_memberships.data]
    workspace_canvases = []
    if workspace_ids:
        response = await authed_client.table("Canvas").select("*").in_("workspace_id", workspace_ids).execute() 
        workspace_canvases = response.data if response.data else []
    all_canvases = personal_canvases + workspace_canvases
    return all_canvases