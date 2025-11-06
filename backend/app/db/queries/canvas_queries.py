from typing import List, Optional, Tuple, Dict, Any # <-- Perbarui impor
from uuid import UUID
from supabase import Client # <-- Tambahkan impor
from postgrest import APIResponse # <-- Tambahkan impor
import logging # <-- Tambahkan impor

logger = logging.getLogger(__name__) # <-- Tambahkan logger

def create_canvas(authed_client: Client, title: str, icon: str, workspace_id: Optional[UUID], creator_id: UUID, user_id: Optional[UUID]) -> Optional[dict]:
    """
    Membuat entri canvas baru di tabel 'Canvas'.  
    """
    payload = {"title": title, "icon": icon, "creator_user_id": str(creator_id)}
    if workspace_id: payload["workspace_id"] = str(workspace_id)
    if user_id: payload["user_id"] = str(user_id)
    
    response = authed_client.table("Canvas").insert(payload).execute() 
    return response.data[0] if response.data else None

# --- FUNGSI LAMA 'get_canvases_in_workspace' DIGANTI DENGAN INI ---
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

# --- FUNGSI LAMA 'get_user_personal_canvases' DIGANTI DENGAN INI ---
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
   
    """
    response = authed_client.table("Canvas").select("*").eq("canvas_id", str(canvas_id)).single().execute()
    return response.data if response.data else None

# ... (sisa fungsi 'get_blocks_in_canvas' dll. tetap sama) ...
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
    # ... (Fungsi ini TIDAK diubah, karena tidak dipaginasi)
    personal_canvases = get_user_personal_canvases_paginated(authed_client, user_id, 0, 1000)[0] # Ambil 1000
    
    workspace_memberships = authed_client.table("WorkspaceMembers").select("workspace_id").eq("user_id", str(user_id)).execute()
    workspace_ids = [m['workspace_id'] for m in workspace_memberships.data]
    
    workspace_canvases = []
    if workspace_ids:
        response = authed_client.table("Canvas").select("*").in_("workspace_id", workspace_ids).execute() 
        workspace_canvases = response.data if response.data else []
    
    all_canvases = personal_canvases + workspace_canvases
    return all_canvases