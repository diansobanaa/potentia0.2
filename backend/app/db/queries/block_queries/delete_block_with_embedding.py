# (Diperbarui untuk AsyncClient native)
from typing import Dict, Any, Optional
from uuid import UUID
# --- PERBAIKAN: Impor AsyncClient ---
from supabase.client import AsyncClient
from postgrest.exceptions import APIError
import logging

logger = logging.getLogger(__name__)

async def delete_block_with_embedding(
    authed_client: AsyncClient, # <-- Tipe diubah
    block_id: UUID
) -> bool:
    """
    (Async Native) Menghapus block dari 'Blocks' dan 'BlocksEmbeddings'.
    """
    embedding_deleted = False
    try:
        logger.info(f"(Query/Delete) Deleting embedding for block {block_id}")
        # --- PERBAIKAN: Gunakan 'await' ---
        await authed_client.table("BlocksEmbeddings") \
            .delete() \
            .eq("block_id", str(block_id)) \
            .execute()
        embedding_deleted = True 
        logger.info(f"(Query/Delete) Embedding deletion attempt finished for block {block_id}.")
    except APIError as e:
        logger.error(f"(Query/Delete) APIError deleting embedding for block {block_id}: {e}")
    except Exception as e:
        logger.error(f"(Query/Delete) Unexpected error deleting embedding for block {block_id}: {e}")

    block_deleted = False
    try:
        logger.info(f"(Query/Delete) Deleting base block {block_id}")
        # --- PERBAIKAN: Gunakan 'await' ---
        response = await authed_client.table("Blocks") \
            .delete() \
            .eq("block_id", str(block_id)) \
            .execute()
        
        block_deleted = bool(response and response.data)
        if block_deleted:
            logger.info(f"(Query/Delete) Base block {block_id} deleted successfully.")
        else:
             logger.warning(f"(Query/Delete) Base block {block_id} not found or failed to delete.")
    except APIError as e:
        logger.error(f"(Query/Delete) APIError deleting base block {block_id}: {e}")
    except Exception as e:
        logger.error(f"(Query/Delete) Unexpected error deleting base block {block_id}: {e}")

    return block_deleted