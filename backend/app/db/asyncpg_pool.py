# File: backend/app/db/asyncpg_pool.py
# (DIPERBAIKI - Menonaktifkan cache statement untuk PgBouncer/Supavisor)

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
    
    if not hasattr(settings, 'DATABASE_URL') or not settings.DATABASE_URL:
        logger.critical("DATABASE_URL tidak diatur di .env atau config.py.")
        raise ValueError("DATABASE_URL tidak diatur. Pool AsyncPG tidak dapat dibuat.")

    try:
        logger.info(f"AsyncPG DSN received: {settings.DATABASE_URL[:50]}...")

        pool = await asyncpg.create_pool(
            dsn=settings.DATABASE_URL,
            min_size=1,
            max_size=5,
            # [PERBAIKAN] Nonaktifkan cache prepared statement
            # Sesuai HINT dari log error asyncpg
            statement_cache_size=0 
        )
        logger.info("Pool koneksi AsyncPG berhasil dibuat (statement_cache_size=0).")
    except Exception as e:
        logger.critical(f"Gagal membuat pool AsyncPG: {e}", exc_info=True)
        raise e

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