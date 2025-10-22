from typing import List, Optional
from uuid import UUID
from app.db.supabase_client import get_supabase_client

supabase = get_supabase_client()

def create_workspace(name: str, workspace_type: str, owner_id: UUID) -> Optional[dict]:
    response = supabase.table("Workspaces").insert({
        "name": name, "type": workspace_type, "owner_user_id": str(owner_id)
    }).execute()
    return response.data[0] if response.data else None

def add_member_to_workspace(workspace_id: UUID, user_id: UUID, role: str) -> Optional[dict]:
    response = supabase.table("WorkspaceMembers").insert({
        "workspace_id": str(workspace_id), "user_id": str(user_id), "role": role
    }).execute()
    return response.data[0] if response.data else None

def get_user_workspaces(user_id: UUID) -> List[dict]:
    response = supabase.table("WorkspaceMembers") \
        .select("Workspaces(*)") \
        .eq("user_id", str(user_id)) \
        .execute()
    return [item["Workspaces"] for item in response.data if item.get("Workspaces")]

def get_workspace_by_id(workspace_id: UUID) -> Optional[dict]:
    response = supabase.table("Workspaces").select("*").eq("workspace_id", str(workspace_id)).single().execute()
    return response.data if response.data else None

def check_user_membership(workspace_id: UUID, user_id: UUID) -> Optional[dict]:
    response = supabase.table("WorkspaceMembers").select("*").eq("workspace_id", str(workspace_id)).eq("user_id", str(user_id)).single().execute()
    return response.data if response.data else None