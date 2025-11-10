# File: backend/app/db/asyncpg_pool.py
# (FILE BARU - Diperlukan untuk pg_notify listener)

import asyncpg
import logging
from app.core.config import settings #

logger = logging.getLogger(__name__)

pool = None

async def create_asyncpg_pool():
    """
    Membuat pool koneksi asyncpg saat startup FastAPI.
    """
    global pool
    if not settings.DATABASE_URL:
        logger.warning("DATABASE_URL tidak diatur. Listener pg_notify (RebalanceWorker) tidak akan berfungsi.")
        return

    try:
        pool = await asyncpg.create_pool(
            dsn=settings.DATABASE_URL,
            min_size=1,
            max_size=5 # Pool kecil, hanya untuk listener
        )
        logger.info("Pool koneksi AsyncPG berhasil dibuat.")
    except Exception as e:
        logger.critical(f"Gagal membuat pool AsyncPG: {e}", exc_info=True)

async def close_asyncpg_pool():
    """
    Menutup pool koneksi asyncpg saat shutdown FastAPI.
    """
    global pool
    if pool:
        await pool.close()
        logger.info("Pool koneksi AsyncPG ditutup.")

def get_asyncpg_pool():
    """
    Dependency injector (atau helper) untuk mendapatkan pool.
    """
    if pool is None:
        raise RuntimeError("Pool AsyncPG belum diinisialisasi. Panggil create_asyncpg_pool() saat startup.")
    return pool