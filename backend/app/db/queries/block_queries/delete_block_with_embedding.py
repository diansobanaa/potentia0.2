# backend\app\db\queries\block_queries\delete_block_with_embedding.py
# (Diperbarui untuk AsyncClient native dan skema v0.4.3)

from typing import Dict, Any, Optional
from uuid import UUID
from supabase.client import AsyncClient
from postgrest.exceptions import APIError
import logging

logger = logging.getLogger(__name__)

async def delete_block_with_embedding(
    authed_client: AsyncClient, # <-- Tipe diubah
    block_id: UUID
) -> bool:
    """
    (Async Native) Menghapus block dari tabel 'Blocks'.
    Logika BlocksEmbeddings sudah dihapus.
    """
    
    block_deleted = False
    try:
        logger.info(f"(Query/Delete) Deleting base block {block_id}")
        # --- PERBAIKAN: Gunakan 'await' ---
        response = await authed_client.table("blocks") \
            .delete() \
            .eq("block_id", str(block_id)) \
            .execute()
        
        block_deleted = bool(response and response.data)
        if block_deleted:
            logger.info(f"(Query/Delete) Base block {block_id} deleted successfully.")
        else:
             logger.warning(f"(Query/Delete) Base block {block_id} not found or failed to delete.")
    except Exception as e:
        logger.error(f"(Query/Delete) Unexpected error deleting base block {block_id}: {e}")

    return block_deleted