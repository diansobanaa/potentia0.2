# PARSE: 20-fix-create-block-v2.py
# (Diperbarui dengan perbaikan 'insert' syntax)

import logging
import asyncio
from typing import Dict, Any, Optional
from uuid import UUID, uuid4
from supabase.client import AsyncClient
from postgrest.exceptions import APIError
from app.services.interfaces import IEmbeddingService 
from app.core.utils.helper import calculate_checksum
from app.core.exceptions import DatabaseError, EmbeddingGenerationError

logger = logging.getLogger(__name__)

async def create_block_and_embedding(
    authed_client: AsyncClient,
    embedding_service: IEmbeddingService, 
    canvas_id: UUID, 
    block_data: Dict[str, Any]
) -> Dict[str, Any]:
    
    block_id = uuid4()
    block_payload = {
        "block_id": str(block_id),
        "canvas_id": str(canvas_id),
        "parent_id": block_data.get("parent_id"),
        "y_order": block_data.get("y_order", 0.0),
        "type": block_data.get("type", "text"),
        "content": block_data.get("content", ""),
        "properties": block_data.get("properties"),
    }

    try:
        logger.info(f"(Query/Create) Inserting base block: {block_id}")
        
        # --- PERBAIKAN: Tambahkan returning="representation" ---
        block_response = await authed_client.table("Blocks") \
            .insert(block_payload, returning="representation") \
            .execute()
        # --------------------------------------------------

        if not (block_response and block_response.data):
            raise DatabaseError("create_block", "Gagal insert block awal")

        created_block = block_response.data[0]
        logger.info(f"(Query/Create) Base block inserted: {block_id}")

        content_to_embed = created_block.get("content")
        embedding = None
        content_checksum = None

        if content_to_embed:
            try:
                embedding = await embedding_service.generate_embedding(
                    content_to_embed,
                    task_type="retrieval_document"
                )
                if not embedding:
                     logger.warning(f"(Query/Create) Gagal generate embedding untuk block {block_id}")
                
                content_checksum = calculate_checksum(content_to_embed)

                if content_checksum:
                    current_metadata = created_block.get("ai_metadata") or {}
                    updated_metadata = {**current_metadata, "content_checksum": content_checksum}
                    
                    logger.info(f"(Query/Create) Updating Blocks ai_metadata for {block_id}...")
                    
                    # (Panggilan 'update' sudah benar, tidak perlu diubah)
                    update_meta_response = await authed_client.table("Blocks") \
                        .update({"ai_metadata": updated_metadata}) \
                        .eq("block_id", str(block_id)) \
                        .execute()
                    
                    if update_meta_response and update_meta_response.data:
                        created_block["ai_metadata"] = updated_metadata

            except Exception as e:
                logger.error(f"Error during embedding/checksum for block {block_id}: {e}", exc_info=True)
                raise EmbeddingGenerationError(f"Gagal embedding/checksum: {e}")

        if embedding and content_checksum:
            embedding_payload = {
                "block_id": str(block_id),
                "canvas_id": str(canvas_id), 
                "content_checksum": content_checksum,
                "embedding": embedding
            }
            try:
                logger.info(f"(Query/Create) Inserting into BlocksEmbeddings for {block_id}")
                
                # --- PERBAIKAN: Tambahkan returning="representation" ---
                embed_response = await authed_client.table("BlocksEmbeddings") \
                    .insert(embedding_payload, returning="representation") \
                    .execute()
                # --------------------------------------------------

                if not (embed_response and embed_response.data):
                    logger.warning(f"(Query/Create) Gagal insert embedding untuk block {block_id}")
                else:
                    logger.info(f"(Query/Create) Embedding inserted for block {block_id}.")
            except Exception as embed_e:
                logger.error(f"(Query/Create) Error inserting embedding for {block_id}: {embed_e}", exc_info=True)
                raise DatabaseError("create_embedding", f"Gagal insert embedding: {embed_e}")

        return created_block

    except Exception as e:
        logger.error(f"(Query/Create) Error fatal di create_block_and_embedding: {e}", exc_info=True)
        await authed_client.table("Blocks").delete().eq("block_id", str(block_id)).execute()
        raise