from typing import List, Optional
from uuid import UUID
from app.db.supabase_client import get_supabase_client

supabase = get_supabase_client()

def create_canvas(title: str, icon: str, workspace_id: Optional[UUID], creator_id: UUID, user_id: Optional[UUID]) -> Optional[dict]:
    payload = {"title": title, "icon": icon, "creator_user_id": str(creator_id)}
    if workspace_id: payload["workspace_id"] = str(workspace_id)
    if user_id: payload["user_id"] = str(user_id)
        
    response = supabase.table("Canvas").insert(payload).execute()
    return response.data[0] if response.data else None

def get_canvases_in_workspace(workspace_id: UUID) -> List[dict]:
    response = supabase.table("Canvas").select("*").eq("workspace_id", str(workspace_id)).eq("is_archived", False).execute()
    return response.data if response.data else []

def get_user_personal_canvases(user_id: UUID) -> List[dict]:
    response = supabase.table("Canvas").select("*").eq("user_id", str(user_id)).eq("is_archived", False).execute()
    return response.data if response.data else []

def get_canvas_by_id(canvas_id: UUID) -> Optional[dict]:
    response = supabase.table("Canvas").select("*").eq("canvas_id", str(canvas_id)).single().execute()
    return response.data if response.data else None

def get_blocks_in_canvas(canvas_id: UUID) -> List[dict]:
    response = supabase.table("Blocks").select("*").eq("canvas_id", str(canvas_id)).order("y_order").execute()
    return response.data if response.data else None

def update_block(block_id: UUID, update_data: dict) -> Optional[dict]:
    response = supabase.table("Blocks").update(update_data).eq("block_id", str(block_id)).execute()
    return response.data[0] if response.data else None

def delete_block(block_id: UUID) -> bool:
    response = supabase.table("Blocks").delete().eq("block_id", str(block_id)).execute()
    return len(response.data) > 0

def get_all_accessible_canvases(user_id: UUID) -> List[dict]:
    """
    Mengambil semua canvas yang bisa diakses user (pribadi + dari workspace).
    Ini adalah implementasi sederhana. Untuk performa lebih baik, buatlah RPC function di Supabase.
    """
    supabase = get_supabase_client()
    
    # 1. Ambil canvas pribadi
    personal_canvases = get_user_personal_canvases(user_id)
    
    # 2. Ambil canvas dari workspace di mana user adalah anggota
    workspace_memberships = supabase.table("WorkspaceMembers").select("workspace_id").eq("user_id", str(user_id)).execute()
    workspace_ids = [m['workspace_id'] for m in workspace_members.data]
    
    workspace_canvases = []
    if workspace_ids:
        response = supabase.table("Canvas").select("*").in_("workspace_id", workspace_ids).execute()
        workspace_canvases = response.data if response.data else []
        
    # 3. Gabungkan keduanya
    all_canvases = personal_canvases + workspace_canvases
    return all_canvases