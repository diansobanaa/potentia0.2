# File: backend/app/core/scheduler.py
# (DIPERBAIKI - Menghapus RedisJobStore yang bermasalah)

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
# HAPUS: from apscheduler.jobstores.redis import RedisJobStore

logger = logging.getLogger(__name__)

# PERBAIKAN: Kembali ke scheduler default (memory-based)
# Persistence ditangani oleh logika restart di dalam worker itu sendiri
scheduler = AsyncIOScheduler()

def setup_scheduler_jobs():
    """
    Mendaftarkan semua background job (Tugas Cron) saat startup.
    """
    logger.info("Mendaftarkan background jobs...")
    
    try:
        # Impor fungsi job dari file 'jobs' (yang sudah ada)
        from app.jobs.schedule_expander import (
            expand_recurring_events_job,
            cleanup_redis_busy_index_job,
            cleanup_old_schedule_instances_job
        )
        
        # Job yang sudah ada
        scheduler.add_job(
            expand_recurring_events_job,
            'interval',
            minutes=5,
            id='job_expand_recurring_events',
            replace_existing=True,
            coalesce=True,
            misfire_grace_time=300
        )

        scheduler.add_job(
            cleanup_redis_busy_index_job,
            'cron',
            hour=2,
            minute=0,
            id='job_cleanup_redis_busy_index',
            replace_existing=True
        )
        
        scheduler.add_job(
            cleanup_old_schedule_instances_job,
            'cron',
            hour=3,
            minute=0,
            id='job_cleanup_old_instances',
            replace_existing=True
        )

        # --- [BARU] DAFTARKAN WORKER UNTUK KOLABORASI CANVAS ---
        logger.info("Mendaftarkan canvas collaboration workers...")
        
        # Impor fungsi worker dari file 'workers'
        from app.workers.rebalance import start_rebalance_worker
        from app.workers.embedding import start_embedding_worker
        from app.workers.cleanup import start_cleanup_worker
        
        # Job untuk Rebalance Worker
        scheduler.add_job(
            start_rebalance_worker,
            'interval',
            minutes=1,
            id='worker_rebalance_starter',
            replace_existing=True,
            max_instances=1
        )
        
        # Job untuk Embedding Worker
        scheduler.add_job(
            start_embedding_worker,
            'interval',
            minutes=1,
            id='worker_embedding_starter',
            replace_existing=True,
            max_instances=1
        )
        
        # Job untuk Cleanup Worker
        scheduler.add_job(
            start_cleanup_worker,
            'cron',
            hour=4,
            minute=0,
            id='worker_cleanup_periodic',
            replace_existing=True,
            max_instances=1
        )

        logger.info("Semua background jobs dan canvas collaboration workers berhasil didaftarkan.")
        
    except ImportError as e:
        logger.warning(f"Gagal mengimpor 'app.jobs' atau 'app.workers'. Melewatkan pendaftaran job. Error: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Error saat mendaftarkan background jobs: {e}", exc_info=True)