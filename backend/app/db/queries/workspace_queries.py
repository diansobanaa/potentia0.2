from typing import List, Optional
from uuid import UUID
from app.models.workspace import MemberRole # Impor MemberRole jika perlu

def create_workspace(authed_client, name: str, workspace_type: str, owner_id: UUID):
    response = authed_client.table("Workspaces").insert({ # <-- GUNAKAN KLIENNYA
        "name": name,
        "type": workspace_type,
        "owner_user_id": str(owner_id)
    }).execute()
    return response.data[0] if response.data else None

def add_member_to_workspace(authed_client, workspace_id: UUID, user_id: UUID, role: MemberRole):
    response = authed_client.table("WorkspaceMembers").insert({ # <-- GUNAKAN KLIENNYA
        "workspace_id": str(workspace_id),
        "user_id": str(user_id),
        "role": role.value # (asumsi 'role' adalah Enum, 'role' saja jika str)
    }).execute()
    return response.data[0] if response.data else None

def get_user_workspaces(authed_client, user_id: UUID) -> List[dict]:
    response = authed_client.table("WorkspaceMembers") \
        .select("Workspaces(*)") \
        .eq("user_id", str(user_id)) \
        .execute()
    # Pastikan mengembalikan list kosong jika tidak ada data
    if not response.data:
        return []
    return [item["Workspaces"] for item in response.data if item.get("Workspaces")]

def get_workspace_by_id(authed_client, workspace_id: UUID) -> Optional[dict]:
    response = authed_client.table("Workspaces").select("*").eq("workspace_id", str(workspace_id)).single().execute()
    return response.data if response.data else None

def check_user_membership(authed_client, workspace_id: UUID, user_id: UUID) -> Optional[dict]:
    response = authed_client.table("WorkspaceMembers").select("*").eq("workspace_id", str(workspace_id)).eq("user_id", str(user_id)).single().execute()
    return response.data if response.data else None