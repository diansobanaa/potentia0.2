from typing import List, Optional
from uuid import UUID

# HAPUS: from app.db.supabase_client import get_supabase_client
# HAPUS: supabase = get_supabase_client()
# Kita tidak lagi menggunakan klien global (anonim). 
# 'authed_client' (klien yang sudah diautentikasi per permintaan) 
# akan diteruskan ke setiap fungsi dari lapisan 'dependencies'.

def create_canvas(authed_client, title: str, icon: str, workspace_id: Optional[UUID], creator_id: UUID, user_id: Optional[UUID]) -> Optional[dict]:
    """
    Membuat entri canvas baru di tabel 'Canvas'.
    Menggunakan klien yang sudah diautentikasi untuk mematuhi RLS.
    """
    payload = {"title": title, "icon": icon, "creator_user_id": str(creator_id)}
    if workspace_id: payload["workspace_id"] = str(workspace_id)
    if user_id: payload["user_id"] = str(user_id)
        
    # Menggunakan 'authed_client' memastikan query ini dijalankan 
    # sebagai pengguna yang sudah login, bukan anonim.
    response = authed_client.table("Canvas").insert(payload).execute() 
    return response.data[0] if response.data else None

def get_canvases_in_workspace(authed_client, workspace_id: UUID) -> List[dict]:
    """
    Mengambil daftar semua canvas yang terkait dengan workspace_id tertentu.
    """
    response = authed_client.table("Canvas").select("*").eq("workspace_id", str(workspace_id)).eq("is_archived", False).execute()
    
    # Selalu kembalikan list (daftar kosong jika tidak ada) 
    # untuk menghindari ResponseValidationError
    return response.data if response.data else []

def get_user_personal_canvases(authed_client, user_id: UUID) -> List[dict]:
    """
    Mengambil daftar semua canvas pribadi milik user_id tertentu.
    """
    response = authed_client.table("Canvas").select("*").eq("user_id", str(user_id)).eq("is_archived", False).execute()
    return response.data if response.data else []

def get_canvas_by_id(authed_client, canvas_id: UUID) -> Optional[dict]:
    """
    Mengambil satu data canvas berdasarkan ID-nya.
    (Ini adalah fungsi yang memperbaiki TypeError Anda sebelumnya)
    """
    response = authed_client.table("Canvas").select("*").eq("canvas_id", str(canvas_id)).single().execute()
    return response.data if response.data else None

# -----------------------------------------------------------------
# Fungsi-fungsi ini sepertinya milik 'block_queries.py',
# tapi jika mereka ada di sini, kita juga perbaiki di sini.
# -----------------------------------------------------------------

def get_blocks_in_canvas(authed_client, canvas_id: UUID) -> List[dict]:
    """
    Mengambil semua block yang terkait dengan canvas_id tertentu.
    """
    response = authed_client.table("Blocks").select("*").eq("canvas_id", str(canvas_id)).order("y_order").execute()
    
    # Selalu kembalikan list (daftar kosong jika tidak ada)
    return response.data if response.data else []

def update_block(authed_client, block_id: UUID, update_data: dict) -> Optional[dict]:
    """
    Memperbarui data dari satu block tertentu.
    """
    response = authed_client.table("Blocks").update(update_data).eq("block_id", str(block_id)).execute()
    return response.data[0] if response.data else None

def delete_block(authed_client, block_id: UUID) -> bool:
    """
    Menghapus satu block tertentu.
    """
    response = authed_client.table("Blocks").delete().eq("block_id", str(block_id)).execute()
    return len(response.data) > 0

def get_all_accessible_canvases(authed_client, user_id: UUID) -> List[dict]:
    """
    Mengambil semua canvas yang bisa diakses user (pribadi + dari workspace).
    Ini menjalankan beberapa query dan menggabungkannya.
    """
    
    # 1. Ambil canvas pribadi (teruskan kliennya)
    personal_canvases = get_user_personal_canvases(authed_client, user_id)
    
    # 2. Ambil canvas dari workspace di mana user adalah anggota (gunakan kliennya)
    workspace_memberships = authed_client.table("WorkspaceMembers").select("workspace_id").eq("user_id", str(user_id)).execute()
    workspace_ids = [m['workspace_id'] for m in workspace_memberships.data]
    
    workspace_canvases = []
    if workspace_ids:
        # Gunakan 'authed_client' untuk query ini
        response = authed_client.table("Canvas").select("*").in_("workspace_id", workspace_ids).execute() 
        workspace_canvases = response.data if response.data else []
        
    # 3. Gabungkan keduanya
    all_canvases = personal_canvases + workspace_canvases
    return all_canvases

