# backend\app\db\queries\block_queries\update_block_and_embedding.py
# PARSE: 22-fix-update-block-v2.py
# (Diperbarui dengan perbaikan 'update' syntax)

import logging
import asyncio
from typing import Dict, Any, Optional, List
from uuid import UUID
from supabase.client import AsyncClient
from postgrest.exceptions import APIError
from app.services.interfaces import IEmbeddingService 
from app.core.utils.helper import calculate_checksum
from app.core.exceptions import DatabaseError, EmbeddingGenerationError

logger = logging.getLogger(__name__)

async def update_block_and_embedding(
    authed_client: AsyncClient,
    embedding_service: IEmbeddingService, 
    block_id: UUID, 
    update_data: Dict[str, Any]
) -> Dict[str, Any]:
    
    logger.info(f"(Query/Update) Memulai pembaruan untuk blok {block_id}")
    new_content = update_data.get("content")
    should_update_embedding = new_content is not None
    
    embedding = None
    content_checksum = None

    try:
        current_block_response = await authed_client.table("Blocks") \
            .select("ai_metadata, canvas_id") \
            .eq("block_id", str(block_id)) \
            .maybe_single() \
            .execute()

        if not current_block_response.data:
            raise DatabaseError("update_block", f"Blok {block_id} tidak ditemukan.")

        current_block = current_block_response.data
        current_metadata = current_block.get("ai_metadata", {}) or {}

        if should_update_embedding:
            content_checksum = calculate_checksum(new_content)
            if current_metadata.get("content_checksum") == content_checksum:
                should_update_embedding = False
                update_data.pop("content", None)
            else:
                try:
                    embedding = await embedding_service.generate_embedding(
                        new_content, task_type="retrieval_document"
                    )
                    if not embedding:
                        should_update_embedding = False
                    else:
                        new_metadata = {**current_metadata, "content_checksum": content_checksum}
                        update_data["ai_metadata"] = new_metadata
                except Exception as e:
                    should_update_embedding = False
        
        if not update_data:
            return current_block 

        logger.info(f"(Query/Update) Memperbarui tabel Blocks untuk {block_id}")
        
        # --- PERBAIKAN: Hapus .single() ---
        update_response = await authed_client.table("Blocks") \
            .update(update_data, returning="representation") \
            .eq("block_id", str(block_id)) \
            .execute()
        # ---------------------------------

        if not update_response.data:
            raise DatabaseError("update_block", f"Gagal memperbarui blok {block_id}.")

        updated_block = update_response.data[0] # Ambil item pertama dari list
        logger.info(f"(Query/Update) Base block {block_id} berhasil diperbarui.")

        if should_update_embedding and embedding and content_checksum:
            embedding_payload = {
                "block_id": str(block_id),
                "canvas_id": str(updated_block["canvas_id"]),
                "content_checksum": content_checksum,
                "embedding": embedding
            }
            try:
                # (Upsert sudah benar)
                await authed_client.table("BlocksEmbeddings") \
                    .upsert(embedding_payload, on_conflict="block_id") \
                    .execute()
                logger.info(f"(Query/Update) Embedding upserted untuk {block_id}.")
            except Exception as embed_e:
                raise DatabaseError("upsert_embedding", f"Gagal upsert embedding: {embed_e}")

        return updated_block

    except Exception as e:
        logger.error(f"(Query/Update) Error fatal di update_block_and_embedding untuk {block_id}: {e}", exc_info=True)
        raise