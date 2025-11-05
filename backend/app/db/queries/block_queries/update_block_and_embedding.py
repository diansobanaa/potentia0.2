# PARSE: 22-fix-update-block-v2.py

import logging
import asyncio  # <-- DIUBAH: Diperlukan untuk non-blocking I/O
from typing import Dict, Any, Optional, List
from uuid import UUID
from supabase import Client as SupabaseClient
from postgrest.exceptions import APIError

# --- DIUBAH: Perbaikan Arsitektur ---
from app.services.interfaces import IEmbeddingService  # Impor INTERFACE
from app.core.utils.helper import calculate_checksum
from app.core.exceptions import DatabaseError, EmbeddingGenerationError
# (Anda tidak perlu 'get_block_by_id' jika kita mengambil data di awal)
# ---

logger = logging.getLogger(__name__) # <-- DIUBAH: Gunakan logger

async def update_block_and_embedding(
    authed_client: SupabaseClient, 
    embedding_service: IEmbeddingService, # <-- DIUBAH: Terima service via DI
    block_id: UUID, 
    update_data: Dict[str, Any]
) -> Dict[str, Any]: # <-- DIUBAH: Kembalikan Dict, raise error jika gagal
    """
    Memperbarui block. Jika 'content' berubah, buat ulang embedding
    dan perbarui tabel 'BlocksEmbeddings' secara non-blocking.
    """
    logger.info(f"(Query/Update) Memulai pembaruan untuk blok {block_id}")
    new_content = update_data.get("content")
    should_update_embedding = new_content is not None
    
    embedding = None
    content_checksum = None

    try:
        # --- Bagian 1: Ambil data blok saat ini (PENTING untuk merge metadata) ---
        logger.info(f"(Query/Update) Mengambil data blok saat ini: {block_id}")
        
        # --- DIUBAH: Non-Blocking ---
        current_block_response = await asyncio.to_thread(
            authed_client.table("Blocks")
                .select("ai_metadata, canvas_id") # Ambil semua yang kita butuhkan
                .eq("block_id", str(block_id))
                .maybe_single()
                .execute
        )

        if not current_block_response.data:
            logger.error(f"(Query/Update) Blok {block_id} tidak ditemukan.")
            raise DatabaseError("update_block", f"Blok {block_id} tidak ditemukan.")

        current_block = current_block_response.data
        current_metadata = current_block.get("ai_metadata", {}) or {}

        # --- Bagian 2: Proses Ulang Embedding jika Konten Berubah ---
        if should_update_embedding:
            logger.info(f"(Query/Update) Konten berubah untuk {block_id}. Memproses embedding...")
            content_checksum = calculate_checksum(new_content)
            
            # Cek jika checksum sama, batalkan update
            if current_metadata.get("content_checksum") == content_checksum:
                logger.info(f"(Query/Update) Checksum sama. Konten tidak berubah. Melewati embedding.")
                should_update_embedding = False
                update_data.pop("content", None) # Hapus 'content' dari payload
            else:
                try:
                    # --- DIUBAH: Panggil method dari service ---
                    embedding = await embedding_service.generate_embedding(
                        new_content,
                        task_type="retrieval_document" # 'document' untuk data yang disimpan
                    )
                    if not embedding:
                        logger.warning(f"(Query/Update) Gagal generate embedding baru untuk {block_id}")
                        should_update_embedding = False
                    else:
                        # Gabungkan metadata baru dengan yang lama
                        new_metadata = {**current_metadata, "content_checksum": content_checksum}
                        update_data["ai_metadata"] = new_metadata
                        
                except Exception as e:
                    logger.error(f"(Query/Update) Error saat proses embedding/checksum: {e}", exc_info=True)
                    should_update_embedding = False # Batalkan update embedding jika error
        
        # Jika tidak ada data tersisa untuk diupdate (misal: hanya 'content' dan itu pun sama)
        if not update_data:
            logger.info(f"(Query/Update) Tidak ada data untuk diupdate pada {block_id}.")
            # Kembalikan data blok yang ada
            return current_block 

        # --- Bagian 3: Update data dasar di tabel Blocks ---
        logger.info(f"(Query/Update) Memperbarui tabel Blocks untuk {block_id}")
        
        # --- DIUBAH: Non-Blocking ---
        update_response = await asyncio.to_thread(
            authed_client.table("Blocks")
                .update(update_data)
                .eq("block_id", str(block_id))
                .select("*") # Kembalikan data yang sudah diupdate
                .single()
                .execute
        )

        if not update_response.data:
            logger.error(f"(Query/Update) Gagal memperbarui base block {block_id}.")
            raise DatabaseError("update_block", f"Gagal memperbarui blok {block_id}.")

        updated_block = update_response.data
        logger.info(f"(Query/Update) Base block {block_id} berhasil diperbarui.")

        # --- Bagian 4: Update/Upsert Embedding ---
        if should_update_embedding and embedding and content_checksum:
            embedding_payload = {
                "block_id": str(block_id),
                "canvas_id": str(updated_block["canvas_id"]),
                "content_checksum": content_checksum,
                "embedding": embedding
            }
            try:
                logger.info(f"(Query/Update) Upserting embedding untuk {block_id}")
                
                # --- DIUBAH: Non-Blocking (Upsert) ---
                await asyncio.to_thread(
                    authed_client.table("BlocksEmbeddings")
                        .upsert(embedding_payload, on_conflict="block_id")
                        .execute
                )
                logger.info(f"(Query/Update) Embedding upserted untuk {block_id}.")
            except Exception as embed_e:
                logger.error(f"(Query/Update) Gagal upsert embedding untuk {block_id}: {embed_e}", exc_info=True)
                # Ini bisa jadi masalah integritas data, jadi kita raise
                raise DatabaseError("upsert_embedding", f"Gagal upsert embedding: {embed_e}")

        return updated_block

    except Exception as e:
        logger.error(f"(Query/Update) Error fatal di update_block_and_embedding untuk {block_id}: {e}", exc_info=True)
        raise # Lempar error ke atas (endpoint)