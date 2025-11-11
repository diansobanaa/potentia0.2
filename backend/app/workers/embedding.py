# File: backend/app/workers/embedding.py
# (DIREFACTOR - Implementasi Circuit Breaker & Logika Job Penuh)

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from uuid import UUID

import redis.asyncio as redis
import pybreaker # <-- [BARU] Impor Circuit Breaker
from supabase.client import AsyncClient
from postgrest import APIResponse

from app.services.embedding_service import GeminiEmbeddingService #
from app.db.supabase_client import get_supabase_admin_async_client
from app.core.config import settings #
from app.core.exceptions import DatabaseError

logger = logging.getLogger(__name__)

# [BARU] Konfigurasi Circuit Breaker (TODO 30)
# Gagal 5 kali berturut-turut
fail_max = 5
# Buka sirkuit selama 60 detik sebelum mencoba lagi
reset_timeout = 60
# Buat instance
gemini_breaker = pybreaker.CircuitBreaker(
    fail_max=fail_max,
    reset_timeout=reset_timeout
)

class EmbeddingWorker:
    """
    Worker untuk menangani proses embedding dengan Circuit Breaker.
    (Lifecycle diperbaiki, Logika Job Penuh)
    """
    
    def __init__(self):
        self.redis_client = redis.from_url(settings.REDIS_URL)
        self.embedding_service = GeminiEmbeddingService()
        self.running = False
        self.task: Optional[asyncio.Task] = None
    
    async def _update_job_status(
        self,
        admin_client: AsyncClient,
        job_id: str,
        status: str,
        error_message: Optional[str] = None
    ):
        """Helper untuk update status job di tabel 'embedding_job_queue'."""
        try:
            await admin_client.table("embedding_job_queue") \
                .update({
                    "status": status,
                    "error_message": error_message,
                    "processed_at": "now()"
                }) \
                .eq("queue_id", job_id) \
                .execute()
        except Exception as e:
            logger.error(f"FATAL: Gagal update status job {job_id}: {e}", exc_info=True)

    @gemini_breaker
    async def _call_embedding_service(self, text: str) -> Optional[list[float]]:
        """
        [BARU] Wrapper untuk memanggil service embedding.
        Wrapper @gemini_breaker akan melempar CircuitBreakerError jika sirkuit terbuka.
        """
        if not text or text.isspace():
            logger.debug("Teks kosong, embedding dilewati.")
            return None
            
        # Panggil service (text-embedding-004)
        # task_type 'retrieval_document' untuk menyimpan ke DB
        return await self.embedding_service.generate_embedding(
            text,
            task_type="retrieval_document" 
        )

    async def _process_job(self, job_info: Dict[str, Any]):
        """
        [REFACTOR] Logika penuh untuk memproses satu job embedding.
        """
        job_id = job_info.get("job_id")
        entity_id = job_info.get("entity_id")
        table_dest = job_info.get("table_destination")
        
        if not all([job_id, entity_id, table_dest]):
            logger.error(f"Job tidak valid, data hilang: {job_info}")
            return

        admin_client: AsyncClient = await get_supabase_admin_async_client()

        try:
            # 1. Ambil Teks Konten dari DB
            # (Saat ini hanya mendukung 'Blocks')
            if table_dest != "blocks":
                raise ValueError(f"Table destination '{table_dest}' tidak didukung.")
            
            response: APIResponse = await admin_client.table("blocks") \
                .select("content") \
                .eq("block_id", entity_id) \
                .maybe_single() \
                .execute()
            
            if not response.data:
                raise NotFoundError(f"Block {entity_id} tidak ditemukan.")
            
            content_text = response.data.get("content")

            # 2. Panggil Service Embedding (via Circuit Breaker)
            vector = await self._call_embedding_service(content_text)
            
            # 3. Simpan Vektor ke DB
            if vector:
                # [PERINGATAN] Pastikan kolom 'vector' Anda
                # di 'migration_001_v0.4.3.sql' adalah VECTOR(768)
                # agar sesuai dengan output Gemini
                await admin_client.table("blocks") \
                    .update({"vector": vector}) \
                    .eq("block_id", entity_id) \
                    .execute()
            
            # 4. Tandai Job Selesai
            await self._update_job_status(admin_client, job_id, "completed")
            logger.info(f"Embedding job {job_id} (Block {entity_id}) selesai.")

        except pybreaker.CircuitBreakerError as e:
            # [BARU] Sirkuit Terbuka! (TODO 30)
            logger.warning(f"Circuit Breaker Terbuka. Job {job_id} gagal: {e}")
            await self._update_job_status(admin_client, job_id, "failed", str(e))
        
        except (DatabaseError, NotFoundError, ValueError) as e:
            # Error yang bisa diprediksi (misal: block tidak ada)
            logger.warning(f"Embedding job {job_id} gagal (error data): {e}")
            await self._update_job_status(admin_client, job_id, "failed", str(e))
            
        except Exception as e:
            # Error tak terduga (misal: API Gemini error, koneksi DB putus)
            logger.error(f"Embedding job {job_id} gagal (runtime error): {e}", exc_info=True)
            await self._update_job_status(admin_client, job_id, "failed", str(e))
            # Biarkan circuit breaker internal menangani kegagalan ini
            if gemini_breaker.state == "closed":
                 # (Ini akan dicatat oleh listener pybreaker jika kita menambahkannya)
                 pass


    async def start(self):
        """
        Memulai worker. (Logika lifecycle tidak berubah dari refactor terakhir)
        """
        if self.task and not self.task.done():
            logger.debug("Embedding worker already running. Skipping start.")
            return
            
        self.running = True
        logger.info("Embedding worker (dengan Circuit Breaker) started")
        self.task = asyncio.create_task(self._run_loop())
    
    async def _run_loop(self):
        """
        Loop utama worker. (Logika lifecycle tidak berubah dari refactor terakhir)
        """
        try:
            while self.running:
                try:
                    # Ambil job dari Redis
                    job_data = await self.redis_client.brpop("embedding_jobs", timeout=5)
                    
                    if job_data:
                        job_json = job_data[1]
                        job_info = json.loads(job_json)
                        await self._process_job(job_info)
                    
                except asyncio.CancelledError:
                    logger.info("Embedding worker loop dibatalkan.")
                    break
                except Exception as e:
                    logger.error(f"Error di embedding worker loop: {e}", exc_info=True)
                    await asyncio.sleep(5)
        finally:
            self.running = False
            self.task = None
            logger.info("Embedding worker loop stopped.")

    def stop(self):
        """
        Menghentikan worker. (Logika lifecycle tidak berubah)
        """
        self.running = False
        if self.task:
            self.task.cancel()
        logger.info("Embedding worker stop requested.")

# (Instance singleton dan fungsi start/stop tetap sama)
embedding_worker = EmbeddingWorker()
async def start_embedding_worker():
    await embedding_worker.start()
def stop_embedding_worker():
    embedding_worker.stop()