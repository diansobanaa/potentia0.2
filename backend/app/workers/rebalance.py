# File: backend/app/workers/rebalance.py
# (DIREFACTOR TOTAL - Beralih dari Redis ke pg_notify)

import asyncio
import logging
from typing import Dict, Any, Optional
from uuid import UUID
import json
import asyncpg

# Impor service yang sudah dipindahkan
from app.services.canvas.lexorank_service import LexoRankService #
from app.core.config import settings #
# Impor pool asyncpg yang baru
from app.db.asyncpg_pool import get_asyncpg_pool

logger = logging.getLogger(__name__)

class RebalanceWorker:
    """
    Worker untuk menangani rebalancing LexoRank.
    Sekarang mendengarkan 'pg_notify'
    """
    
    def __init__(self):
        # Hapus 'redis_client'
        self.lexorank_service = LexoRankService()
        self.running = False
        self.task: Optional[asyncio.Task] = None 
        self.connection = None

    async def start(self):
        """
        Memulai worker. (Logika start/stop tetap sama)
        """
        if self.task and not self.task.done():
            logger.debug("Rebalance worker already running. Skipping start.")
            return
            
        self.running = True
        logger.info("Rebalance worker started (mode pg_notify).")
        
        self.task = asyncio.create_task(self._run_loop())
    
    async def _notification_listener(self, conn):
        """Callback untuk menangani notifikasi yang masuk."""
        try:
            notification = await conn.wait_for_notification(timeout=60.0)
            if notification is None:
                # Timeout, kirim ping untuk jaga koneksi
                await conn.execute("SELECT 1")
                return
            
            logger.info(f"Menerima notifikasi rebalance: {notification.payload}")
            
            # Parse payload
            payload = json.loads(notification.payload)
            canvas_id = UUID(payload["canvas_id"])
            
            # Panggil rebalance (jangan 'await' agar listener bisa lanjut)
            asyncio.create_task(self._process_rebalance(canvas_id))
            
        except asyncpg.exceptions.InterfaceError as e:
            # Koneksi terputus
            logger.error(f"Koneksi listener rebalance terputus: {e}. Mencoba koneksi ulang...")
            self.running = False # Picu restart di _run_loop
        except Exception as e:
            logger.error(f"Error di listener notifikasi: {e}", exc_info=True)
            await asyncio.sleep(5)

    async def _process_rebalance(self, canvas_id: UUID):
        """Wrapper untuk memanggil service rebalance dengan aman."""
        try:
            logger.info(f"Rebalancing canvas {canvas_id}...")
            await self.lexorank_service.rebalance(canvas_id)
            logger.info(f"Rebalanced canvas {canvas_id} sukses.")
        except Exception as e:
            logger.error(f"Gagal rebalance canvas {canvas_id}: {e}", exc_info=True)

    async def _run_loop(self):
        """
        [REFACTOR] Loop utama worker, sekarang menggunakan asyncpg LISTEN.
        """
        try:
            pool = get_asyncpg_pool()
            async with pool.acquire() as conn:
                self.connection = conn
                await conn.add_listener('rebalance_needed', self._notification_listener)
                logger.info("Rebalance worker listening ke channel 'rebalance_needed'.")
                
                while self.running:
                    # Cek jika koneksi masih hidup
                    if self.connection.is_closed():
                        logger.warning("Koneksi RebalanceWorker terputus, loop berhenti.")
                        break
                    await asyncio.sleep(1) # Loop utama hanya tidur
                    
        except asyncio.CancelledError:
            logger.info("Rebalance worker loop dibatalkan.")
        except Exception as e:
            logger.error(f"Error di rebalance worker loop: {e}", exc_info=True)
        finally:
            self.running = False
            self.task = None
            if self.connection and not self.connection.is_closed():
                try:
                    await self.connection.remove_listener('rebalance_needed', self._notification_listener)
                except Exception as e:
                    logger.warning(f"Gagal remove listener: {e}")
            logger.info("Rebalance worker loop stopped.")

    def stop(self):
        """
        Menghentikan worker.
        """
        self.running = False
        if self.task:
            self.task.cancel()
        logger.info("Rebalance worker stop requested.")

# (Instance singleton dan fungsi start/stop tetap sama)
rebalance_worker = RebalanceWorker()
async def start_rebalance_worker():
    await rebalance_worker.start()
def stop_rebalance_worker():
    rebalance_worker.stop()