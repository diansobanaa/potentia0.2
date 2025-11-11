# File: backend/db/queries/canvas/canvas_queries.py
# (DIPERBAIKI - Sintaks .update() yang salah)

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from supabase.client import AsyncClient
from postgrest import APIResponse 

from app.models.canvas import CanvasCreate #
from app.core.exceptions import DatabaseError, NotFoundError

logger = logging.getLogger(__name__)

# ... (Fungsi create_canvas_db, get_user_canvases_db ... tidak berubah)
# ... (Salin dari file canvas_queries.py Anda sebelumnya)

async def create_canvas_db(
    admin_client: AsyncClient, 
    canvas_data: CanvasCreate, 
    creator_id: UUID
) -> Dict[str, Any]:
    # (Implementasi tidak berubah)
    payload = {
        "title": canvas_data.title,
        "icon": canvas_data.icon,
        "creator_user_id": str(creator_id),
        "canvas_metadata": canvas_data.canvas_metadata or {}
    }
    if canvas_data.workspace_id:
        payload["workspace_id"] = str(canvas_data.workspace_id)
    try:
        response: APIResponse = await admin_client.table("canvas") \
            .insert(payload, returning="representation") \
            .execute()
        if not response.data:
            raise DatabaseError("create_canvas_db", "Gagal membuat canvas.")
        return response.data[0]
    except Exception as e:
        logger.error(f"Error di create_canvas_db: {e}", exc_info=True)
        raise DatabaseError("create_canvas_db", str(e))

async def get_user_canvases_db(
    admin_client: AsyncClient, 
    user_id: UUID, 
    limit: int, 
    offset: int
) -> List[Dict[str, Any]]:
    # (Implementasi tidak berubah)
    user_id_str = str(user_id)
    try:
        ws_response: APIResponse = await admin_client.table("workspace_members") \
            .select("workspace_id") \
            .eq("user_id", user_id_str) \
            .execute()
        workspace_ids = [m["workspace_id"] for m in ws_response.data or []]
        personal_resp: APIResponse = await admin_client.table("canvas") \
            .select("*") \
            .eq("creator_user_id", user_id_str) \
            .is_("workspace_id", "null") \
            .eq("is_archived", False) \
            .execute()
        direct_resp: APIResponse = await admin_client.table("canvas_access") \
            .select("Canvas(*)") \
            .eq("user_id", user_id_str) \
            .eq("Canvas.is_archived", False) \
            .execute()
        workspace_canvases = []
        if workspace_ids:
            workspace_canvas_resp: APIResponse = await admin_client.table("canvas") \
                .select("*") \
                .in_("workspace_id", workspace_ids) \
                .eq("is_archived", False) \
                .execute()
            workspace_canvases = workspace_canvas_resp.data or []
        all_canvases = (personal_resp.data or []) + \
                       [item["canvas"] for item in (direct_resp.data or []) if item.get("canvas")] + \
                       workspace_canvases
        seen_ids = set()
        unique_canvases = []
        for canvas in all_canvases:
            if canvas["canvas_id"] not in seen_ids:
                seen_ids.add(canvas["canvas_id"])
                unique_canvases.append(canvas)
        unique_canvases.sort(key=lambda x: x.get("updated_at", x.get("created_at", "")), reverse=True)
        return unique_canvases[offset : offset + limit]
    except Exception as e:
        logger.error(f"Error di get_user_canvases_db: {e}", exc_info=True)
        raise DatabaseError("get_user_canvases_db", str(e))

async def update_canvas_db(
    admin_client: AsyncClient, 
    canvas_id: UUID, 
    update_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Memperbarui detail canvas di database.
    [PERBAIKAN] Memindahkan 'returning' ke dalam '.update()'
    """
    try:
        response: APIResponse = await admin_client.table("canvas") \
            .update(update_data, returning="representation") \
            .eq("canvas_id", str(canvas_id)) \
            .execute()
        
        if not response.data:
            raise NotFoundError("update_canvas_db", f"Canvas dengan ID {canvas_id} tidak ditemukan untuk diupdate.")
            
        return response.data[0]
            
    except Exception as e:
        logger.error(f"Error di update_canvas_db: {e}", exc_info=True)
        raise DatabaseError("update_canvas_db", str(e))

async def delete_canvas_db(
    admin_client: AsyncClient, 
    canvas_id: UUID
):
    # (Implementasi tidak berubah)
    try:
        response: APIResponse = await admin_client.table("canvas") \
            .delete() \
            .eq("canvas_id", str(canvas_id)) \
            .returning("representation") \
            .execute()
        if not response.data:
            raise NotFoundError("delete_canvas_db", f"Canvas {canvas_id} tidak ditemukan.")
    except Exception as e:
        logger.error(f"Error di delete_canvas_db: {e}", exc_info=True)
        raise DatabaseError("delete_canvas_db", str(e))

async def get_canvas_blocks_db_rpc(
    admin_client: AsyncClient, 
    canvas_id: UUID, 
    limit: int, 
    offset: int
) -> List[Dict[str, Any]]:
    # (Implementasi tidak berubah)
    try:
        response: APIResponse = await admin_client.rpc(
            "get_blocks_by_canvas",
            {"p_canvas_id": str(canvas_id), "p_limit": limit, "p_offset": offset}
        ).execute()
        return response.data or []
    except Exception as e:
        logger.error(f"Error di get_canvas_blocks_db_rpc: {e}", exc_info=True)
        raise DatabaseError("get_canvas_blocks_db_rpc", str(e))


async def get_canvas_with_access_db(
    admin_client: AsyncClient, 
    canvas_id: UUID, 
    user_id: UUID
) -> Dict[str, Any]:
    # (Implementasi tidak berubah dari perbaikan terakhir)
    user_id_str = str(user_id)
    try:
        canvas_response = await admin_client.table("canvas") \
            .select("*") \
            .eq("canvas_id", str(canvas_id)) \
            .maybe_single() \
            .execute()
        
        if not canvas_response: 
            raise NotFoundError("get_canvas_with_access_db", f"Canvas dengan ID {canvas_id} tidak ditemukan.")
        
        canvas = canvas_response.data
        
        access_info = {
            "canvas": canvas,
            "user_id": user_id,
            "role": "viewer",
            "is_owner": False,
            "is_creator": False
        }
        
        if canvas.get("creator_user_id") == user_id_str:
            access_info["is_creator"] = True
            access_info["is_owner"] = True
            access_info["role"] = "owner"
            return access_info
        
        if canvas.get("user_id") == user_id_str:
            access_info["is_owner"] = True
            access_info["role"] = "owner"
            return access_info
        
        if canvas.get("workspace_id"):
            ws_resp: APIResponse = await admin_client.table("workspace_members") \
                .select("role") \
                .eq("workspace_id", canvas["workspace_id"]) \
                .eq("user_id", user_id_str) \
                .maybe_single() \
                .execute()
            
            if ws_resp and ws_resp.data:
                workspace_role = ws_resp.data["role"]
                if workspace_role == "admin":
                    access_info["is_owner"] = True
                    access_info["role"] = "admin"
                elif workspace_role == "editor":
                    access_info["role"] = "editor"
        
        access_resp: APIResponse = await admin_client.table("canvas_access") \
            .select("role") \
            .eq("canvas_id", str(canvas_id)) \
            .eq("user_id", user_id_str) \
            .maybe_single() \
            .execute()
        
        if access_resp and access_resp.data:
            access_info["role"] = access_resp.data["role"]

        return access_info
            
    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error di get_canvas_with_access_db: {e}", exc_info=True)
        raise DatabaseError("get_canvas_with_access_db", str(e))