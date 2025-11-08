# File: backend/app/db/queries/schedule_queries.py
# (Diperbarui untuk AsyncClient native)

from typing import List, Optional, Dict, Any
from uuid import UUID
import logging
# --- PERBAIKAN: Impor AsyncClient ---
from supabase.client import AsyncClient
from postgrest import APIResponse
from app.core.exceptions import DatabaseError
# ------------------------------------

logger = logging.getLogger(__name__)

async def create_schedule_legacy(
    authed_client: AsyncClient, # <-- Tipe diubah
    schedule_data: dict
) -> Optional[dict]:
    """
    (Async Native) Membuat jadwal (versi lama).
    """
    try:
        # --- PERBAIKAN: Gunakan 'await' dan returning="representation" ---
        response = await authed_client.table("Schedules") \
            .insert(schedule_data, returning="representation") \
            .execute()
        # -----------------------------------------------------------
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Error create_schedule_legacy (async): {e}", exc_info=True)
        raise DatabaseError("create_schedule_legacy", str(e))


async def get_schedules_in_workspace(
    authed_client: AsyncClient, # <-- Tipe diubah
    workspace_id: UUID
) -> List[dict]:
    """
    (Async Native) Mengambil jadwal (versi lama) di workspace.
    """
    try:
        # --- PERBAIKAN: Gunakan 'await' ---
        response = await authed_client.table("Schedules") \
            .select("*") \
            .eq("workspace_id", str(workspace_id)) \
            .execute()
        # --------------------------------
        return response.data if response.data else []
    except Exception as e:
        logger.error(f"Error get_schedules_in_workspace (async): {e}", exc_info=True)
        return []