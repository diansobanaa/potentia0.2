# backend\app\db\queries\block_queries\create_block_and_embedding.py
# PARSE: 20-fix-create-block-v2.py
# (Diperbarui dengan perbaikan 'insert' syntax dan skema v0.4.3)

import logging
import asyncio
from typing import Dict, Any, Optional
from uuid import UUID, uuid4
from supabase.client import AsyncClient
from postgrest.exceptions import APIError
from app.services.interfaces import IEmbeddingService 
from app.core.utils.helper import calculate_checksum
from app.core.exceptions import DatabaseError, EmbeddingGenerationError
from datetime import datetime # DITAMBAHKAN

logger = logging.getLogger(__name__)

async def create_block_and_embedding(
    authed_client: AsyncClient,
    embedding_service: IEmbeddingService, 
    canvas_id: UUID, 
    block_data: Dict[str, Any],
    user_id: UUID # DITAMBAHKAN: Creator user ID untuk audit
) -> Dict[str, Any]:
    
    block_id = uuid4()
    # Pastikan y_order adalah string untuk LexoRank
    y_order_value = block_data.get("y_order") if isinstance(block_data.get("y_order"), str) else "a0"
    
    block_payload = {
        "block_id": str(block_id),
        "canvas_id": str(canvas_id),
        "parent_id": block_data.get("parent_id"),
        "y_order": y_order_value, # DIUBAH
        "type": block_data.get("type", "text"),
        "content": block_data.get("content", ""),
        "properties": block_data.get("properties"),
        "created_by": str(user_id), # DITAMBAHKAN: Audit
        "updated_by": str(user_id), # DITAMBAHKAN: Audit
    }

    try:
        logger.info(f"(Query/Create) Inserting base block: {block_id}")
        
        block_response = await authed_client.table("Blocks") \
            .insert(block_payload, returning="representation") \
            .execute()

        if not (block_response and block_response.data):
            raise DatabaseError("create_block", "Gagal insert block awal")

        created_block = block_response.data[0]
        logger.info(f"(Query/Create) Base block inserted: {block_id}")

        content_to_embed = created_block.get("content")
        embedding = None
        content_checksum = None

        if content_to_embed:
            try:
                # 2. GENERATE EMBEDDING & CHECKSUM
                embedding = await embedding_service.generate_embedding(
                    content_to_embed,
                    task_type="retrieval_document"
                )
                if not embedding:
                     logger.warning(f"(Query/Create) Gagal generate embedding untuk block {block_id}")
                
                content_checksum = calculate_checksum(content_to_embed)
            except Exception as e:
                logger.error(f"Error during embedding/checksum for block {block_id}: {e}", exc_info=True)
                # JANGAN raise EmbeddingGenerationError; ini adalah background task
                pass 

        if embedding and content_checksum:
            current_metadata = created_block.get("ai_metadata") or {}
            updated_metadata = {**current_metadata, "content_checksum": content_checksum}
            
            update_payload = {
                "ai_metadata": updated_metadata,
                "vector": embedding, # DIUBAH: Vektor langsung ke tabel Blocks
                "updated_at": datetime.utcnow().isoformat(), # DITAMBAHKAN: Audit
            }
            
            logger.info(f"(Query/Create) Updating Blocks ai_metadata & vector for {block_id}...")
            
            update_meta_response = await authed_client.table("Blocks") \
                .update(update_payload) \
                .eq("block_id", str(block_id)) \
                .execute()
            
            if update_meta_response and update_meta_response.data:
                # Gabungkan hasil update ke objek block yang dikembalikan
                created_block = {**created_block, **update_payload}
                created_block["ai_metadata"] = updated_metadata
            
        # LOGIKA LAMA untuk BlocksEmbeddings DIHAPUS (Task 13)

        return created_block

    except Exception as e:
        logger.error(f"(Query/Create) Error fatal di create_block_and_embedding: {e}", exc_info=True)
        # Lakukan cleanup jika gagal total
        await authed_client.table("Blocks").delete().eq("block_id", str(block_id)).execute()
        raise