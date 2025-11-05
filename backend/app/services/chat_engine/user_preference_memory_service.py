#app\services\chat_engine\user_preference_memory_service.py
from __future__ import annotations
import logging
import asyncio
from uuid import UUID
from typing import List, Dict, Any, TYPE_CHECKING
from supabase import Client as SupabaseClient # Ganti dengan AsyncClient jika Anda menggunakannya

# --- PERUBAHAN ---
# Impor fungsi baru dari lokasi file yang benar
from app.db.queries.conversation.user_preference import execute_batch_inserts
# --- AKHIR PERUBAHAN ---

# Impor ini akan bergantung pada di mana Anda mendefinisikan EmbeddingService
# dari app.core.dependencies import EmbeddingServiceDep (Contoh)

# Untuk type hinting, asumsikan EmbeddingService memiliki metode ini
if TYPE_CHECKING:
    class EmbeddingService:
        async def generate_embedding(self, text: str, task_type: str) -> List[float]:
            ...

logger = logging.getLogger(__name__)

# Kategori Tipe (Berdasarkan Arsitektur Kita)
# Ini memberi tahu "Perute Data" ke mana harus mengirim data.
SQL_RELATIONAL_TYPES = [
    "PROFIL_PENGGUNA", 
    "GAYA_BAHASA", 
    "FORMAT", 
    "LARANGAN"
]
VECTOR_SEMANTIC_TYPES = [
    "MEMORI", 
    "TUJUAN_PENGGUNA", 
    "TOPIK", 
    "KENDALA_TUGAS"
]


async def save_preferences_to_db(
    # --- PERUBAHAN ---
    authed_client: SupabaseClient, # Diubah agar konsisten
    # --- AKHIR PERUBAHAN ---
    embedding_service: EmbeddingService,
    user_id: UUID,
    preferences_list: List[Dict[str, Any]]
):
    """
    "Perute Data" (Data Router) Asinkron.
    
    Fungsi ini mengambil list preferensi yang diekstrak oleh Asesor (Panggilan #3)
    dan merutekannya ke database yang tepat (SQL Relasional atau Vektor Semantik)
    berdasarkan 'type' preferensi.
    """
    if not preferences_list:
        logger.info(f"Tidak ada preferensi baru untuk disimpan bagi user {user_id}.")
        return

    logger.info(f"Memulai penyimpanan {len(preferences_list)} preferensi untuk user {user_id}...")

    # Dua "ember" untuk batch insert
    sql_insert_batch = []
    vector_content_to_embed = []
    
    # -----------------------------------------------------------
    # TAHAP 1: Sortir preferensi ke dalam ember yang tepat
    # -----------------------------------------------------------
    for pref in preferences_list:
        pref_type = pref.get("type")
        description = pref.get("description")
        
        if not pref_type or not description:
            logger.warning(f"Melewatkan preferensi karena 'type' atau 'description' tidak ada: {pref}")
            continue

        # Data untuk kedua tabel
        # Data untuk kedua tabel
        base_data = {
            "user_id": str(user_id), # KONVERSI UUID KE STRING
            "trigger_text": pref.get("trigger_text"),
            "confidence_score": pref.get("confidence_score", 0.0),
            "type": pref_type
        }

        if pref_type in SQL_RELATIONAL_TYPES:
            # --- Ember 1: SQL Relasional (user_preferences) ---
            sql_data = base_data.copy()
            sql_data.update({
                # --- PERBAIKAN (Sesuai Keputusan Anda) ---
                # 'preference_id' DIHAPUS dari payload.
                # Kita biarkan database mengisinya secara otomatis
                # dengan 'default gen_random_uuid()'.
                # -----------------------------------------
                "description": description,
                "priority": 0 # Default priority
            })
            sql_insert_batch.append(sql_data)
        
        elif pref_type in VECTOR_SEMANTIC_TYPES:
            # --- Ember 2: Vektor Semantik (user_semantic_memories) ---
            vector_data = base_data.copy()
            vector_data["content"] = description
            vector_content_to_embed.append(vector_data) # user_id di sini sudah string
            
        else:
            logger.warning(f"Tipe preferensi tidak dikenal: {pref_type}. Melewatkan.")

    # -----------------------------------------------------------
    # TAHAP 2: Proses & Batch Insert Ember Vektor (Dengan Embedding)
    # -----------------------------------------------------------
    vector_insert_batch = []
    if vector_content_to_embed:
        logger.info(f"Membuat {len(vector_content_to_embed)} embedding untuk memori semantik...")
        
        # Buat semua embedding secara paralel (jauh lebih cepat)
        embedding_tasks = [
            embedding_service.generate_embedding(
                text=item["content"], 
                task_type="retrieval_document" # Gunakan tipe dokumen untuk penyimpanan
            ) for item in vector_content_to_embed
        ]
        embeddings = await asyncio.gather(*embedding_tasks)
        
        # Gabungkan data dengan embedding-nya
        for item, embedding in zip(vector_content_to_embed, embeddings):
            if embedding:
                item_with_embedding = item.copy()
                item_with_embedding["embedding"] = embedding
                vector_insert_batch.append(item_with_embedding)
            else:
                logger.warning(f"Gagal membuat embedding for content: {item['content']}")

    # -----------------------------------------------------------
    # TAHAP 3: Eksekusi Batch Inserts ke DB (DIPINDAHKAN)
    # -----------------------------------------------------------
    try:
        # Panggil fungsi eksternal yang sekarang menangani logika DB
        await execute_batch_inserts(
            authed_client, # Diubah agar konsisten
            user_id,
            sql_insert_batch,
            vector_insert_batch
        )
            
    except Exception as e:
        logger.error(f"Gagal saat memanggil execute_batch_inserts untuk user {user_id}: {e}", exc_info=True)
        # Jangan melempar error di sini, karena ini adalah background task.
        # Respons ke pengguna sudah dikirim.

