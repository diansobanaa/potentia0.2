from typing import Optional
from app.db.supabase_client import get_supabase_client

supabase = get_supabase_client()
_SUPER_MASTER_PROMPT_CACHE: Optional[str] = None

def get_super_master_prompt() -> str:
    """
    Mengambil Super Master Prompt dari database.
    Menggunakan cache sederhana untuk performa.
    """
    global _SUPER_MASTER_PROMPT_CACHE
    if _SUPER_MASTER_PROMPT_CACHE:
        return _SUPER_MASTER_PROMPT_CACHE

    try:
        response = supabase.table("SuperMasterPrompt").select("description").eq("type", "Konstanta").single().execute()
        if response.data:
            _SUPER_MASTER_PROMPT_CACHE = response.data["description"]
            return _SUPER_MASTER_PROMPT_CACHE
    except Exception as e:
        print(f"Error fetching Super Master Prompt from DB: {e}")

    return "Kamu adalah asisten AI yang profesional dan membantu."