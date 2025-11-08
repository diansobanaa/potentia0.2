# app/services/chat_engine/user_preference_memory_service.py
# (Diperbarui untuk AsyncClient native)

from __future__ import annotations
import logging
import asyncio
from uuid import UUID
from typing import List, Dict, Any, TYPE_CHECKING
# --- PERBAIKAN: Impor AsyncClient ---
from supabase.client import AsyncClient
# ------------------------------------
from app.db.queries.conversation.user_preference import execute_batch_inserts

if TYPE_CHECKING:
    class EmbeddingService:
        async def generate_embedding(self, text: str, task_type: str) -> List[float]:
            ...

logger = logging.getLogger(__name__)

SQL_RELATIONAL_TYPES = ["PROFIL_PENGGUNA", "GAYA_BAHASA", "FORMAT", "LARANGAN"]
VECTOR_SEMANTIC_TYPES = ["MEMORI", "TUJUAN_PENGGUNA", "TOPIK", "KENDALA_TUGAS"]

async def save_preferences_to_db(
    authed_client: AsyncClient, # <-- Tipe diubah
    embedding_service: EmbeddingService,
    user_id: UUID,
    preferences_list: List[Dict[str, Any]]
):
    """
    (Async Native) "Perute Data" Asinkron.
    """
    if not preferences_list:
        logger.info(f"Tidak ada preferensi baru untuk disimpan bagi user {user_id}.")
        return

    logger.info(f"Memulai penyimpanan {len(preferences_list)} preferensi untuk user {user_id}...")

    sql_insert_batch = []
    vector_content_to_embed = []
    
    # TAHAP 1: Sortir (Logika tidak berubah)
    for pref in preferences_list:
        pref_type = pref.get("type")
        description = pref.get("description")
        if not pref_type or not description: continue

        base_data = {
            "user_id": str(user_id),
            "trigger_text": pref.get("trigger_text"),
            "confidence_score": pref.get("confidence_score", 0.0),
            "type": pref_type
        }
        if pref_type in SQL_RELATIONAL_TYPES:
            sql_data = base_data.copy()
            sql_data.update({"description": description, "priority": 0})
            sql_insert_batch.append(sql_data)
        elif pref_type in VECTOR_SEMANTIC_TYPES:
            vector_data = base_data.copy()
            vector_data["content"] = description
            vector_content_to_embed.append(vector_data)
        else:
            logger.warning(f"Tipe preferensi tidak dikenal: {pref_type}. Melewatkan.")

    # TAHAP 2: Proses Vektor (Logika tidak berubah, 'generate_embedding' sudah async)
    vector_insert_batch = []
    if vector_content_to_embed:
        logger.info(f"Membuat {len(vector_content_to_embed)} embedding untuk memori semantik...")
        
        embedding_tasks = [
            embedding_service.generate_embedding(
                text=item["content"], 
                task_type="retrieval_document"
            ) for item in vector_content_to_embed
        ]
        embeddings = await asyncio.gather(*embedding_tasks)
        
        for item, embedding in zip(vector_content_to_embed, embeddings):
            if embedding:
                item_with_embedding = item.copy()
                item_with_embedding["embedding"] = embedding
                vector_insert_batch.append(item_with_embedding)
            else:
                logger.warning(f"Gagal membuat embedding for content: {item['content']}")

    # TAHAP 3: Eksekusi Batch Inserts (Async Native)
    try:
        # Panggil fungsi 'execute_batch_inserts' (yang sudah di-refaktor)
        await execute_batch_inserts(
            authed_client,
            user_id,
            sql_insert_batch,
            vector_insert_batch
        )
            
    except Exception as e:
        logger.error(f"Gagal saat memanggil execute_batch_inserts (async) untuk user {user_id}: {e}", exc_info=True)