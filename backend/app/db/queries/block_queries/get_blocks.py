# (Diperbarui untuk AsyncClient native)
from typing import List, Optional, Dict, Any
from uuid import UUID
from postgrest.exceptions import APIError
# --- PERBAIKAN: Impor AsyncClient ---
from supabase.client import AsyncClient
import logging # <-- [DITAMBAHKAN]

logger = logging.getLogger(__name__) # <-- [DITAMBAHKAN]

async def get_blocks_in_canvas(
    authed_client: AsyncClient, # <-- Tipe diubah
    canvas_id: UUID
) -> List[dict]:
    """
    (Async Native) Mengambil semua block dalam canvas, diurutkan.
    """
    try:
        # --- PERBAIKAN: Gunakan 'await' ---
        response = await authed_client.table("blocks") \
            .select("*") \
            .eq("canvas_id", str(canvas_id)) \
            .order("y_order") \
            .execute()
        return response.data if response and response.data else []
    except APIError as e:
        logger.error(f"(Query/Get) APIError getting blocks (async) {canvas_id}: {e}")
        return []
    except Exception as e:
        logger.error(f"(Query/Get) Unexpected error getting blocks (async) {canvas_id}: {e}")
        return []

async def get_block_by_id(
    authed_client: AsyncClient, # <-- Tipe diubah
    block_id: UUID
) -> Optional[Dict[str, Any]]:
     """
     (Async Native) Mengambil satu block berdasarkan ID-nya.
     """
     try:
        # --- PERBAIKAN: Gunakan 'await' ---
        response = await authed_client.table("blocks") \
            .select("*") \
            .eq("block_id", str(block_id)) \
            .maybe_single() \
            .execute()
        return response.data if response and response.data else None
     except APIError as e:
        logger.error(f"(Query/Get) APIError getting block (async) {block_id}: {e}")
        return None
     except Exception as e:
        logger.error(f"(Query/Get) Unexpected error getting block (async) {block_id}: {e}")
        return None