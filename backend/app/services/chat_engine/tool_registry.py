# backend/app/services/chat_engine/tool_registry.py

import logging
from uuid import UUID
from typing import List, Dict, Any, Optional
from langchain_core.tools import tool
from supabase import Client as SupabaseClient
# from app.db.queries import canvas_queries, schedule_queries # (ASUMSI FILE QUERIES ADA)
from app.models.user import User

logger = logging.getLogger(__name__)

class PotentiaTools:
    """Class yang berisi semua Tools LangChain untuk di-inject ke Agent Utama."""
    def __init__(self, client: SupabaseClient, user: User):
        self.client = client
        self.user = user

    @tool("get_user_canvases")
    def get_user_canvases_tool(self, workspace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Gunakan ini untuk MENGAMBIL daftar canvas yang dapat diakses oleh pengguna. 
        Input: workspace_id (opsional) atau None untuk mendapatkan canvas pribadi.
        (Saat ini mengembalikan mock)
        """
        return {"result": [{"canvas_id": "MOCK_CANVAS_ID", "title": "Dashboard Proyek Q3"}]}
    
    @tool("create_new_schedule")
    def create_new_schedule_tool(self, title: str, workspace_id: str) -> Dict[str, Any]:
        """
        Gunakan ini untuk MENAMBAH TUGAS (schedule) baru untuk pengguna.
        (Saat ini mengembalikan mock)
        """
        return {"result": f"Tugas baru '{title}' berhasil dibuat di workspace {workspace_id}."}
    
# Tambahkan fungsi factory untuk tools list Anda di sini jika diperlukan
def get_tools_list(client: SupabaseClient, user: User) -> List:
    tools_instance = PotentiaTools(client, user)
    return [
        tools_instance.get_user_canvases_tool, 
        tools_instance.create_new_schedule_tool
    ]