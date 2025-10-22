from uuid import UUID
from app.db.supabase_client import get_supabase_client

supabase = get_supabase_client()

def log_action(user_id: UUID, action: str, details: dict):
    supabase.table("AuditLog").insert({
        "user_id": str(user_id), "action": action, "details": details
    }).execute()