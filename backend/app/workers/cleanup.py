# File: backend/app/workers/cleanup.py
# (DIPERBAIKI - Bug Resource Leak)

import asyncio
import logging
from typing import Dict, Any, List
from uuid import UUID
import json

import redis.asyncio as redis

from app.core.config import settings #
from app.db.supabase_client import get_supabase_admin_async_client

logger = logging.getLogger(__name__)

class CleanupWorker:
    """
    Worker untuk membersihkan data yang tidak lagi diperlukan.
    (Sekarang menjalankan tugas satu kali per panggilan, bukan loop abadi)
    Sumber:
    """
    
    def __init__(self):
        self.redis_client = redis.from_url(settings.REDIS_URL)
        # Tidak ada lagi 'self.running' atau 'self.task'
    
    async def run_cleanup_cycle(self):
        """
        [PERBAIKAN] Menjalankan satu siklus cleanup.
        Dihapus: 'while self.running' dan 'asyncio.sleep(300)'
        """
        logger.info("Cleanup worker cycle started")
        try:
            await self._cleanup_expired_presence()
            await self._retry_failed_embedding_jobs()
            logger.info("Cleanup worker cycle finished")
        except Exception as e:
            logger.error(f"Error in cleanup worker cycle: {e}", exc_info=True)

    async def _cleanup_expired_presence(self):
        """
        Membersihkan data presence yang sudah kadaluwarsa dari Redis.
        (Logika tidak berubah)
        Sumber:
        """
        try:
            cursor = "0"
            while True:
                cursor, keys = await self.redis_client.scan(cursor, match="user_presence:*", count=100)
                
                if keys:
                    for key in keys:
                        ttl = await self.redis_client.ttl(key)
                        if ttl == -1:
                            await self.redis_client.expire(key, 300)
                
                if cursor == 0 or cursor == b'0':
                    break
            
            logger.debug("Presence cleanup completed")
        except Exception as e:
            logger.error(f"Error during presence cleanup: {e}", exc_info=True)

    async def _retry_failed_embedding_jobs(self):
        """
        Memproses kembali embedding job yang gagal dengan retry limit.
        (Logika tidak berubah)
        Sumber:
        """
        try:
            admin_client = await get_supabase_admin_async_client()
            
            response = await admin_client.table("embedding_job_queue") \
                .select("*") \
                .eq("status", "failed") \
                .lt("retry_count", 3) \
                .execute()
            
            failed_jobs = response.data or []
            
            for job in failed_jobs:
                job_id = job["queue_id"]
                
                await admin_client.table("embedding_job_queue") \
                    .update({
                        "status": "pending",
                        "error_message": None,
                        "retry_count": job["retry_count"] + 1
                    }) \
                    .eq("queue_id", job_id) \
                    .execute()
                
                await self.redis_client.lpush(
                    "embedding_jobs",
                    json.dumps({
                        "job_id": str(job_id),
                        "entity_id": job["fk_id"],
                        "table_destination": job["table_destination"]
                    })
                )
                logger.info(f"Retrying embedding job {job_id}")
            
            if failed_jobs:
                logger.info(f"Retried {len(failed_jobs)} failed embedding jobs")
            
        except Exception as e:
            logger.error(f"Error during embedding job retry: {e}", exc_info=True)

# Singleton instance
cleanup_worker = CleanupWorker()

# Fungsi yang dipanggil oleh scheduler
async def start_cleanup_worker():
    """
    Fungsi wrapper yang dipanggil oleh scheduler.
    [PERBAIKAN] Memanggil 'run_cleanup_cycle'
    Sumber:
    """
    await cleanup_worker.run_cleanup_cycle()

# Fungsi stop tidak lagi relevan karena task-nya berumur pendek
def stop_cleanup_worker():
    """
    Fungsi untuk menghentikan worker saat shutdown.
    (Tidak ada lagi loop abadi untuk dihentikan)
    """
    logger.info("Cleanup worker shutdown (no long-running task to stop).")
    pass