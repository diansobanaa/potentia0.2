# File: backend/app/core/scheduler.py
# (Menggantikan placeholder Anda)

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.redis import RedisJobStore
from app.core.config import settings

logger = logging.getLogger(__name__)

# Konfigurasi JobStore menggunakan Redis
# Ini adalah fallback krusial: job tetap ada (persistent)
# bahkan jika server FastAPI di-restart.
jobstores = {
    'default': RedisJobStore(
        host=settings.REDIS_URL.split('//')[-1].split(':')[0],
        port=int(settings.REDIS_URL.split(':')[-1]),
        db=1 # Gunakan DB #1 agar terpisah dari cache (jika ada)
    )
}

# Inisialisasi scheduler
# Kita gunakan 'asyncio' agar terintegrasi dengan event loop FastAPI
scheduler = AsyncIOScheduler(jobstores=jobstores)

def setup_scheduler_jobs():
    """
    Mendaftarkan semua background job (Tugas Cron) saat startup.
    """
    logger.info("Mendaftarkan background jobs...")
    
    try:
        # Impor fungsi job dari file 'jobs'
        from app.jobs.schedule_expander import (
            expand_recurring_events_job,
            cleanup_redis_busy_index_job,
            cleanup_old_schedule_instances_job
        )
        
        # TODO-SVC-2: Job untuk ekspansi RRULE
        # Dijadwalkan setiap 5 menit (bisa diubah nanti)
        scheduler.add_job(
            expand_recurring_events_job,
            'interval',
            minutes=5,
            id='job_expand_recurring_events',
            replace_existing=True,
            coalesce=True, # Mencegah job berjalan tumpuk jika > 5 menit
            misfire_grace_time=300 # Toleransi 5 menit jika server mati
        )

        # TODO-SVC-5: Job untuk membersihkan Redis ZSET
        scheduler.add_job(
            cleanup_redis_busy_index_job,
            'cron',
            hour=2, # Setiap jam 2 pagi
            minute=0,
            id='job_cleanup_redis_busy_index',
            replace_existing=True
        )
        
        # Job opsional untuk membersihkan 'ScheduleInstances'
        scheduler.add_job(
            cleanup_old_schedule_instances_job,
            'cron',
            hour=3, # Setiap jam 3 pagi
            minute=0,
            id='job_cleanup_old_instances',
            replace_existing=True
        )

        logger.info("Semua background jobs berhasil didaftarkan.")
        
    except ImportError as e:
        logger.warning(f"Gagal mengimpor 'app.jobs'. Melewatkan pendaftaran job. Error: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Error saat mendaftarkan background jobs: {e}", exc_info=True)