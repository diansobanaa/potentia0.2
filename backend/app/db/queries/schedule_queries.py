from typing import List, Optional
from uuid import UUID
from app.db.supabase_client import get_supabase_client

supabase = get_supabase_client()

def create_schedule(schedule_data: dict) -> Optional[dict]:
    response = supabase.table("Schedules").insert(schedule_data).execute()
    return response.data[0] if response.data else None

def get_schedules_in_workspace(workspace_id: UUID) -> List[dict]:
    response = supabase.table("Schedules").select("*").eq("workspace_id", str(workspace_id)).execute()
    return response.data if response.data else None