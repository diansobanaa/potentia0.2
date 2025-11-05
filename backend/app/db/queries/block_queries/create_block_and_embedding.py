# PARSE: 20-fix-create-block-v2.py

import logging
import asyncio # <-- DIUBAH: Diperlukan untuk non-blocking I/O
from typing import Dict, Any, Optional
from uuid import UUID, uuid4
from supabase import Client as SupabaseClient
from postgrest.exceptions import APIError

# --- DIUBAH: Perbaikan Arsitektur ---
# Impor INTERFACE, bukan implementasi
from app.services.interfaces import IEmbeddingService 
# Impor helper Anda
from app.core.utils.helper import calculate_checksum
# Impor exceptions
from app.core.exceptions import DatabaseError, EmbeddingGenerationError
# ---

logger = logging.getLogger(__name__) # <-- DIUBAH: Gunakan logger

async def create_block_and_embedding(
    authed_client: SupabaseClient, 
    embedding_service: IEmbeddingService, # <-- DIUBAH: Terima service via DI
    canvas_id: UUID, 
    block_data: Dict[str, Any]
) -> Dict[str, Any]: # <-- DIUBAH: Kembalikan Dict, raise error jika gagal
    """
    Membuat block baru dan embeddingnya secara non-blocking.
    Bergantung pada IEmbeddingService yang di-inject.
    """
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
        # 2. INSERT ke tabel Blocks (Non-Blocking)
        logger.info(f"(Query/Create) Inserting base block: {block_id}")
        
        # --- DIUBAH: Jalankan I/O sinkron di thread terpisah ---
        block_response = await asyncio.to_thread(
            authed_client.table("Blocks").insert(block_payload).execute
        )

        if not (block_response and block_response.data):
            logger.error(f"(Query/Create) Gagal insert block {block_id} untuk canvas {canvas_id}.")
            raise DatabaseError("create_block", "Gagal insert block awal")

        created_block = block_response.data[0]
        logger.info(f"(Query/Create) Base block inserted: {block_id}")

        # --- Bagian Embedding dan Checksum ---
        content_to_embed = created_block.get("content")
        embedding = None
        content_checksum = None

        if content_to_embed:
            try:
                # 3. Generate Embedding (sudah async)
                # --- DIUBAH: Panggil method dari service ---
                embedding = await embedding_service.generate_embedding(
                    content_to_embed,
                    task_type="retrieval_document" # 'document' untuk data yang disimpan
                )
                if not embedding:
                     logger.warning(f"(Query/Create) Gagal generate embedding untuk block {block_id}")
                
                # 4. Hitung Checksum
                content_checksum = calculate_checksum(content_to_embed)

                # 5. Update ai_metadata di tabel Blocks (Non-Blocking)
                if content_checksum:
                    current_metadata = created_block.get("ai_metadata") or {}
                    updated_metadata = {**current_metadata, "content_checksum": content_checksum}
                    
                    logger.info(f"(Query/Create) Updating Blocks ai_metadata for {block_id}...")
                    
                    # --- DIUBAH: Jalankan I/O sinkron di thread terpisah ---
                    update_meta_response = await asyncio.to_thread(
                        authed_client.table("Blocks")
                            .update({"ai_metadata": updated_metadata})
                            .eq("block_id", str(block_id))
                            .execute
                    )
                    
                    if update_meta_response and update_meta_response.data:
                        created_block["ai_metadata"] = updated_metadata
                        logger.info(f"(Query/Create) ai_metadata updated for block {block_id}.")
                    else:
                        logger.warning(f"(Query/Create) Gagal update ai_metadata untuk block {block_id}")

            except Exception as e:
                logger.error(f"Error during embedding/checksum for block {block_id}: {e}", exc_info=True)
                # Jika embedding gagal, kita harus rollback?
                # Untuk saat ini, kita anggap non-fatal tapi raise error
                raise EmbeddingGenerationError(f"Gagal embedding/checksum: {e}")

        # 6. INSERT ke tabel BlocksEmbeddings (Non-Blocking)
        if embedding and content_checksum:
            embedding_payload = {
                "block_id": str(block_id),
                "canvas_id": str(canvas_id), 
                "content_checksum": content_checksum,
                "embedding": embedding
            }
            try:
                logger.info(f"(Query/Create) Inserting into BlocksEmbeddings for {block_id}")
                
                # --- DIUBAH: Jalankan I/O sinkron di thread terpisah ---
                embed_response = await asyncio.to_thread(
                    authed_client.table("BlocksEmbeddings").insert(embedding_payload).execute
                )

                if not (embed_response and embed_response.data):
                    logger.warning(f"(Query/Create) Gagal insert embedding untuk block {block_id}")
                else:
                    logger.info(f"(Query/Create) Embedding inserted for block {block_id}.")
            except Exception as embed_e:
                logger.error(f"(Query/Create) Error inserting embedding for {block_id}: {embed_e}", exc_info=True)
                # Ini bisa jadi masalah integritas data, jadi kita raise
                raise DatabaseError("create_embedding", f"Gagal insert embedding: {embed_e}")
        else:
             logger.info(f"(Query/Create) Skipping embedding insert for block {block_id}.")

        return created_block

    except Exception as e:
        logger.error(f"(Query/Create) Error fatal di create_block_and_embedding: {e}", exc_info=True)
        # Hapus block yang mungkin sudah dibuat untuk rollback
        await asyncio.to_thread(
             authed_client.table("Blocks").delete().eq("block_id", str(block_id)).execute
        )
        raise # Lempar error ke atas (endpoint)