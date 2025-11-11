# backend\app\db\queries\block_queries\update_block_and_embedding.py
# (Diperbarui dengan perbaikan 'update' syntax dan skema v0.4.3)

import logging
import asyncio
from typing import Dict, Any, Optional, List
from uuid import UUID
from supabase.client import AsyncClient
from postgrest.exceptions import APIError
from app.services.interfaces import IEmbeddingService 
from app.core.utils.helper import calculate_checksum
from app.core.exceptions import DatabaseError, EmbeddingGenerationError
from datetime import datetime # DITAMBAHKAN

logger = logging.getLogger(__name__)

async def update_block_and_embedding(
    authed_client: AsyncClient,
    embedding_service: IEmbeddingService, 
    block_id: UUID, 
    update_data: Dict[str, Any],
    user_id: UUID # DITAMBAHKAN: Updater user ID untuk audit
) -> Dict[str, Any]:
    
    logger.info(f"(Query/Update) Memulai pembaruan untuk blok {block_id}")
    new_content = update_data.get("content")
    should_update_embedding = new_content is not None
    
    embedding = None
    content_checksum = None

    try:
        # 1. Ambil data block saat ini (perlu kolom version)
        current_block_response = await authed_client.table("blocks") \
            .select("ai_metadata, canvas_id, version") \
            .eq("block_id", str(block_id)) \
            .maybe_single() \
            .execute()

        if not current_block_response.data:
            raise DatabaseError("update_block", f"Blok {block_id} tidak ditemukan.")

        current_block = current_block_response.data
        current_metadata = current_block.get("ai_metadata", {}) or {}
        current_version = current_block.get("version", 1)
        
        # 2. Tambahkan kolom audit dan version update
        update_data["updated_by"] = str(user_id) # DITAMBAHKAN: Audit
        update_data["updated_at"] = datetime.utcnow().isoformat() # DITAMBAHKAN: Audit
        update_data["version"] = current_version + 1 # DITAMBAHKAN: Optimistic Lock (Increment)

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
                        update_data["vector"] = embedding # DIUBAH: Vektor langsung ke tabel Blocks
                        update_data["ai_metadata"] = new_metadata
                except Exception as e:
                    should_update_embedding = False
        
        if not update_data:
            return current_block 

        logger.info(f"(Query/Update) Memperbarui tabel Blocks untuk {block_id}")
        
        # NOTE: Implementasi Real-Time Production akan menambahkan: .eq("version", current_version)
        # untuk Optimistic Lock, tapi kita lewati dulu untuk menghindari perubahan di RPC.
        response: APIResponse = await authed_client.table("blocks") \
            .update(update_data, returning="representation") \
            .eq("block_id", str(block_id)) \
            .execute()
        
        if not response.data:
            # Jika menggunakan Optimistic Lock, ini bisa berarti konflik (Version Mismatch)
            raise DatabaseError("update_block", f"Gagal memperbarui blok {block_id} (Data tidak ditemukan).")

        updated_block = response.data[0] 
        logger.info(f"(Query/Update) Base block {block_id} berhasil diperbarui.")

        # LOGIKA LAMA untuk BlocksEmbeddings DIHAPUS (Task 13)

        return updated_block

    except Exception as e:
        logger.error(f"(Query/Update) Error fatal di update_block_and_embedding untuk {block_id}: {e}", exc_info=True)
        raise