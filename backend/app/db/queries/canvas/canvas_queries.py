# File: backend/app/db/queries/canvas/canvas_queries.py
from typing import List, Optional, Tuple, Dict, Any 
from uuid import UUID
from supabase import Client
from postgrest import APIResponse, APIError
import logging
import asyncio 
from app.core.exceptions import DatabaseError, NotFoundError

logger = logging.getLogger(__name__)

def create_canvas(authed_client: Client, title: str, icon: str, workspace_id: Optional[UUID], creator_id: UUID, user_id: Optional[UUID]) -> Optional[dict]:
    """
    Membuat entri canvas baru di tabel 'Canvas'.  
    """
    payload = {"title": title, "icon": icon, "creator_user_id": str(creator_id)}
    if workspace_id: payload["workspace_id"] = str(workspace_id)
    if user_id: payload["user_id"] = str(user_id)
    
    response = authed_client.table("Canvas").insert(payload).execute() 
    return response.data[0] if response.data else None

async def update_canvas_metadata(
    authed_client: Client, 
    canvas_id: UUID, 
    update_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Memperbarui HANYA metadata canvas (judul, ikon).
    Dijalankan secara non-blocking.
    """
    
    def sync_db_call() -> Dict[str, Any]:
        """Fungsi sinkron untuk dijalankan di thread terpisah."""
        try:
            response: APIResponse = (
                authed_client.table("Canvas")
                .update(update_data, returning="representation")
                .eq("canvas_id", str(canvas_id))
                # .single() # <-- [DIHAPUS] Ini adalah penyebab error
                .execute()
            )
            
            # [FALLBACK BARU]
            # Jika update berhasil, 'response.data' akan berisi
            # list dengan 1 elemen.
            if not response.data or len(response.data) == 0:
                # Ini seharusnya tidak terjadi jika dependency 'get_canvas_access'
                # lolos, tapi ini adalah fallback yang tangguh.
                raise NotFoundError("Canvas tidak ditemukan saat proses update metadata.")
            
            # Kembalikan elemen pertama dari list
            return response.data[0]
            
        except NotFoundError:
             raise
        except Exception as e:
            logger.error(f"Error saat update metadata canvas (sync) {canvas_id}: {e}", exc_info=True)
            raise DatabaseError("update_canvas_meta_sync", str(e))
    
    try:
        updated_data = await asyncio.to_thread(sync_db_call)
        return updated_data
    except Exception as e:
        logger.error(f"Error di update_canvas_metadata (async) {canvas_id}: {e}", exc_info=True)
        if isinstance(e, (DatabaseError, NotFoundError)):
            raise 
        raise DatabaseError("update_canvas_meta_async", f"Error tidak terduka: {str(e)}")

# --- [FUNGSI DIPERBAIKI 2: Update Status Arsip] ---
async def set_canvas_archived_status(
    authed_client: Client, 
    canvas_id: UUID, 
    is_archived: bool
) -> Dict[str, Any]:
    """
    Memperbarui HANYA status 'is_archived' dari canvas.
    Dijalankan secara non-blocking.
    """
    update_data = {"is_archived": is_archived}
    
    def sync_db_call() -> Dict[str, Any]:
        """Fungsi sinkron untuk dijalankan di thread terpisah."""
        try:
            response: APIResponse = (
                authed_client.table("Canvas")
                .update(update_data, returning="representation")
                .eq("canvas_id", str(canvas_id))
                # .single() # <-- [DIHAPUS] Ini adalah penyebab error
                .execute()
            )

            # [FALLBACK BARU]
            if not response.data or len(response.data) == 0:
                raise NotFoundError("Canvas tidak ditemukan saat update status arsip.")
            
            # Kembalikan elemen pertama dari list
            return response.data[0]
            
        except NotFoundError:
             raise
        except Exception as e:
            logger.error(f"Error saat set status arsip canvas (sync) {canvas_id}: {e}", exc_info=True)
            raise DatabaseError("set_canvas_archive_sync", str(e))

    try:
        updated_data = await asyncio.to_thread(sync_db_call)
        return updated_data
    except Exception as e:
        logger.error(f"Error di set_canvas_archived_status (async) {canvas_id}: {e}", exc_info=True)
        if isinstance(e, (DatabaseError, NotFoundError)):
            raise 
        raise DatabaseError("set_canvas_archive_async", f"Error tidak terduka: {str(e)}")

    
async def delete_canvas(
    authed_client: Client, 
    canvas_id: UUID
) -> bool:
    """
    Menghapus canvas (Hard Delete) dari database.
    (Sekarang aman dari crash 404 karena dependency).
    """
    def sync_db_call() -> bool:
        try:
            response: APIResponse = (
                authed_client.table("Canvas")
                .delete(returning="representation")
                .eq("canvas_id", str(canvas_id))
                .execute()
            )
            return bool(response.data and len(response.data) > 0)
        except Exception as e:
            logger.error(f"Error saat delete canvas (sync) {canvas_id}: {e}", exc_info=True)
            if "violates foreign key constraint" in str(e):
                raise DatabaseError("delete_canvas_fk", "Canvas tidak dapat dihapus karena masih memiliki block di dalamnya.")
            raise DatabaseError("delete_canvas_sync", str(e))

    try:
        success = await asyncio.to_thread(sync_db_call)
        if not success:
            # Fallback jika canvas tidak ada (dependency harusnya sudah menangkap ini,
            # tapi ini adalah pengaman ganda).
            raise NotFoundError("Canvas tidak ditemukan untuk dihapus.")
        logger.info(f"Canvas {canvas_id} berhasil dihapus (hard delete).")
        return True
    
    except Exception as e:
        logger.error(f"Error di delete_canvas (async) untuk {canvas_id}: {e}", exc_info=True)
        if isinstance(e, (DatabaseError, NotFoundError)):
            raise 
        raise DatabaseError("delete_canvas_async", f"Error tidak terduka: {str(e)}")


def get_canvases_in_workspace_paginated(
    authed_client: Client, 
    workspace_id: UUID, 
    offset: int, 
    limit: int
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Mengambil daftar canvas di workspace dengan pagination dan total count.
    """
    try:
        # 1. Ambil data yang dipaginasi
        list_response: APIResponse = authed_client.table("Canvas") \
            .select("*") \
            .eq("workspace_id", str(workspace_id)) \
            .eq("is_archived", False) \
            .order("updated_at", desc=True) \
            .range(offset, offset + limit - 1) \
            .execute()

        # 2. Hitung total
        count_response: APIResponse = authed_client.table("Canvas") \
            .select("canvas_id", count="exact") \
            .eq("workspace_id", str(workspace_id)) \
            .eq("is_archived", False) \
            .execute()
        
        data = list_response.data or []
        total = count_response.count or 0
        return data, total
    
    except Exception as e:
        logger.error(f"Error paginating workspace canvases for {workspace_id}: {e}", exc_info=True)
        return [], 0 # Kembalikan nilai aman jika error

def get_user_personal_canvases_paginated(
    authed_client: Client, user_id: UUID, offset: int, limit: int
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Mengambil daftar canvas pribadi user dengan pagination dan total count.
    """
    try:
        # 1. Ambil data yang dipaginasi
        list_response: APIResponse = authed_client.table("Canvas") \
            .select("*") \
            .eq("user_id", str(user_id)) \
            .eq("is_archived", False) \
            .order("updated_at", desc=True) \
            .range(offset, offset + limit - 1) \
            .execute()

        # 2. Hitung total
        count_response: APIResponse = authed_client.table("Canvas") \
            .select("canvas_id", count="exact") \
            .eq("user_id", str(user_id)) \
            .eq("is_archived", False) \
            .execute()
        
        data = list_response.data or []
        total = count_response.count or 0
        return data, total
    except Exception as e:
        logger.error(f"Error paginating personal canvases for {user_id}: {e}", exc_info=True)
        return [], 0 # Kembalikan nilai aman jika error


def get_canvas_by_id(authed_client: Client, canvas_id: UUID) -> Optional[dict]:
    """
    Mengambil satu data canvas berdasarkan ID-nya.
    (Fungsi sinkron, dipanggil oleh dependency 'get_canvas_access')
    
    [VERSI DIPERBAIKI] - Sekarang menangani 'response' yang None
    dan semua exceptions.
    """
    try:
        # Panggilan database
        response: APIResponse = (
            authed_client.table("Canvas")
            .select("*")
            .eq("canvas_id", str(canvas_id))
            .maybe_single() # Gunakan maybe_single untuk 0 atau 1 baris
            .execute()
        )
        
        # --- FALLBACK 1: Cek jika 'response' itu sendiri None ---
        if response is None:
            # Ini terjadi jika .execute() gagal secara tak terduga
            logger.warning(f"get_canvas_by_id: Supabase client mengembalikan 'None' untuk canvas {canvas_id}.")
            return None

        # --- FALLBACK 2: Cek jika 'response.data' kosong (valid 404) ---
        if not response.data:
            # Ini adalah kasus normal "tidak ditemukan"
            logger.info(f"get_canvas_by_id: Canvas {canvas_id} tidak ditemukan di DB.")
            return None
            
        # Jika lolos, kembalikan data
        return response.data

    except APIError as e:
        # Menangani error PostgREST (misal: 406 Not Acceptable)
        logger.error(f"APIError di get_canvas_by_id untuk {canvas_id}: {e.message}", exc_info=True)
        return None
    except Exception as e:
        # Menangani error Python (seperti AttributeError jika terjadi lagi)
        logger.error(f"Error umum di get_canvas_by_id untuk {canvas_id}: {e}", exc_info=True)
        return None
    

async def check_user_canvas_access(
    authed_client: Client, 
    canvas_id: UUID, 
    user_id: UUID
) -> Optional[Dict[str, Any]]:
    """
    Memeriksa apakah pengguna memiliki akses langsung ke canvas 
    melalui tabel 'CanvasAccess' (logika invite).
    """
    
    def sync_db_call() -> Optional[Dict[str, Any]]:
        try:
            response: APIResponse = (
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
            logger.error(f"Error saat check_user_canvas_access (sync): {e}", exc_info=True)
            return None
    try:
        access_data = await asyncio.to_thread(sync_db_call)
        return access_data
    except Exception as e:
        logger.error(f"Error di check_user_canvas_access (async): {e}", exc_info=True)
        return None
            
    
def get_blocks_in_canvas(authed_client, canvas_id: UUID) -> List[dict]:
    response = authed_client.table("Blocks").select("*").eq("canvas_id", str(canvas_id)).order("y_order").execute()
    return response.data if response.data else []

def update_block(authed_client, block_id: UUID, update_data: dict) -> Optional[dict]:
    response = authed_client.table("Blocks").update(update_data).eq("block_id", str(block_id)).execute()
    return response.data[0] if response.data else None

def delete_block(authed_client, block_id: UUID) -> bool:
    response = authed_client.table("Blocks").delete().eq("block_id", str(block_id)).execute()
    return len(response.data) > 0

def get_all_accessible_canvases(authed_client, user_id: UUID) -> List[dict]:
    personal_canvases = get_user_personal_canvases_paginated(authed_client, user_id, 0, 1000)[0] # Ambil 1000
    
    workspace_memberships = authed_client.table("WorkspaceMembers").select("workspace_id").eq("user_id", str(user_id)).execute()
    workspace_ids = [m['workspace_id'] for m in workspace_memberships.data]
    
    workspace_canvases = []
    if workspace_ids:
        response = authed_client.table("Canvas").select("*").in_("workspace_id", workspace_ids).execute() 
        workspace_canvases = response.data if response.data else []
    
    all_canvases = personal_canvases + workspace_canvases
    return all_canvases