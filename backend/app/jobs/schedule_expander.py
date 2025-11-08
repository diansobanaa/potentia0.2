# File: backend/app/jobs/schedule_expander.py
# (Menggantikan placeholder Anda)

import logging
import asyncio
from uuid import UUID
from datetime import datetime, timedelta
from typing import List, Dict, Any, Set, Tuple
from dateutil.rrule import rrule, rrulestr, rruleset
from dateutil.parser import parse as dt_parse
import pytz # Diperlukan untuk penanganan UTC

# Impor untuk DB dan Redis
from app.db.supabase_client import get_supabase_client
from app.services.redis_rate_limiter import redis_client # (Menggunakan redis_client yang ada)

# Impor Kueri yang telah kita buat
from app.db.queries.calendar.calendar_queries import (
    get_calendar_subscribers,
    get_schedules_needing_expansion,
    bulk_delete_instances_for_schedule,
    bulk_insert_instances
)
from app.core.exceptions import DatabaseError

logger = logging.getLogger(__name__)

# --- TODO: Implementasi Redis Lock (saat ini placeholder) ---
# Untuk mencegah job ini berjalan di >1 server (jika di-scale)
# Kita bisa gunakan lock sederhana:
# if not redis_client.set("lock:expand_rrule_job", "running", ex=300, nx=True):
#    logger.warning("[JOB] Ekspansi RRULE dilewati, job lain sedang berjalan.")
#    return
# ... (logika job) ...
# redis_client.delete("lock:expand_rrule_job")


def _generate_timestamps(
    schedule: Dict[str, Any],
    start_range: datetime,
    end_range: datetime
) -> List[Tuple[datetime, datetime]]:
    """
    Helper untuk menghitung (ekspansi) RRULE.
    Menggunakan 'rrule', 'rdate', dan 'exdate' (RFC 5545).
    """
    instances = []
    
    # Pastikan start/end adalah 'aware' (memiliki info timezone)
    if schedule['start_time'].tzinfo is None:
        schedule['start_time'] = schedule['start_time'].replace(tzinfo=pytz.UTC)
    if schedule['end_time'].tzinfo is None:
        schedule['end_time'] = schedule['end_time'].replace(tzinfo=pytz.UTC)

    duration = schedule['end_time'] - schedule['start_time']
    
    # 1. Buat RRuleSet
    ruleset = rruleset()
    
    # 2. Tambahkan Aturan Perulangan (RRULE)
    if schedule.get('rrule'):
        # 'dtstart' adalah jangkar dari perulangan
        ruleset.rrule(rrulestr(schedule['rrule'], dtstart=schedule['start_time']))
        
    # 3. Tambahkan Tanggal Spesifik (RDATE)
    if schedule.get('rdate'):
        for rdate_str in schedule['rdate']:
            try:
                ruleset.rdate(dt_parse(rdate_str).replace(tzinfo=pytz.UTC))
            except Exception:
                pass # Abaikan rdate yang invalid

    # 4. Hapus Tanggal Pengecualian (EXDATE)
    if schedule.get('exdate'):
        for exdate_str in schedule['exdate']:
            try:
                ruleset.exdate(dt_parse(exdate_str).replace(tzinfo=pytz.UTC))
            except Exception:
                pass # Abaikan exdate yang invalid

    # 5. Hitung (Generate) instances di antara rentang waktu
    try:
        for dt_start in ruleset.between(start_range, end_range):
            dt_end = dt_start + duration
            instances.append((dt_start, dt_end))
    except Exception as e:
         logger.error(f"Gagal ekspansi rrule untuk schedule {schedule['schedule_id']}: {e}", exc_info=True)

    # 6. Jika tidak ada aturan perulangan (bukan RRULE),
    #    tambahkan acara tunggal itu sendiri jika masuk rentang
    if not schedule.get('rrule'):
        if schedule['start_time'] <= end_range and schedule['end_time'] >= start_range:
            instances.append((schedule['start_time'], schedule['end_time']))

    return instances


async def expand_and_populate_instances(schedule_id: UUID):
    """
    [Implementasi TODO-SVC-2 (Revisi)]
    Melakukan ekspansi RRULE untuk SATU schedule_id dan
    mengisi ulang 'ScheduleInstances' untuk SEMUA subscriber.
    """
    logger.info(f"[JOB] Memulai ekspansi untuk schedule_id: {schedule_id}")
    
    # Kita butuh admin client untuk job ini
    admin_client = get_supabase_client()
    
    try:
        # Ambil data schedule (source of truth)
        # (Kita asumsikan 'get_schedule_by_id' perlu dibuat)
        schedule_response = await asyncio.to_thread(
            admin_client.table("schedules").select("*").eq("schedule_id", str(schedule_id)).single().execute
        )
        if not schedule_response.data:
            logger.error(f"[JOB] Gagal ekspansi: Schedule {schedule_id} tidak ditemukan.")
            return

        schedule = schedule_response.data
        calendar_id = schedule.get('calendar_id')
        
        # 1. Ambil SEMUA subscribers (Kunci "MUST FIX")
        subscribers = await get_calendar_subscribers(admin_client, calendar_id)
        if not subscribers:
            logger.warning(f"[JOB] Melewatkan schedule {schedule_id}, tidak ada subscriber di kalender {calendar_id}.")
            return

        # 2. Hapus semua instance lama untuk schedule ini
        #    Ini membersihkan semua user sekaligus (efisien)
        logger.debug(f"[JOB] Menghapus instance lama untuk {schedule_id}...")
        await bulk_delete_instances_for_schedule(admin_client, schedule_id)

        # 3. Hitung (Ekspansi) timestamps (misal: 2 tahun ke depan)
        now = datetime.now(pytz.UTC)
        start_range = now - timedelta(days=30) # Ekspansi 30 hari ke belakang
        end_range = now + timedelta(days=730)  # Ekspansi 2 tahun ke depan
        
        instances_timestamps = _generate_timestamps(schedule, start_range, end_range)

        if not instances_timestamps:
            logger.info(f"[JOB] Tidak ada instance ditemukan (atau acara sudah lewat) untuk {schedule_id}.")
            return

        # 4. Buat Batch Insert (Denormalisasi N x M)
        instances_batch = []
        user_ids_affected: Set[UUID] = set() # Untuk invalidasi cache

        for user_sub in subscribers:
            user_id = user_sub.get('user_id')
            if not user_id:
                continue
            
            user_ids_affected.add(UUID(user_id))
            
            for dt_start, dt_end in instances_timestamps:
                instances_batch.append({
                    "schedule_id": str(schedule_id),
                    "calendar_id": str(calendar_id),
                    "user_id": str(user_id), # <-- Denormalisasi (MUST FIX)
                    "start_time": dt_start.isoformat(),
                    "end_time": dt_end.isoformat(),
                    "is_exception": False # TODO: Tambah logika pengecualian
                })

        # 5. Eksekusi Bulk Insert
        if instances_batch:
            logger.info(f"[JOB] Menyisipkan {len(instances_batch)} instance baru untuk {schedule_id} (melayani {len(subscribers)} subscriber).")
            await bulk_insert_instances(admin_client, instances_batch)
        
        # 6. Invalidasi Cache Redis (TODO-SVC-4)
        if user_ids_affected:
            logger.info(f"[JOB] Meng-invalidasi cache free/busy untuk {len(user_ids_affected)} pengguna...")
            redis_keys_to_delete = [f"busy_index:{str(uid)}" for uid in user_ids_affected]
            await asyncio.to_thread(redis_client.delete, *redis_keys_to_delete)

    except Exception as e:
        logger.error(f"[JOB] Gagal total saat ekspansi schedule {schedule_id}: {e}", exc_info=True)


async def expand_recurring_events_job():
    """
    [Implementasi TODO-SVC-2]
    Job utama yang berjalan periodik.
    """
    logger.info("[JOB] Memulai job 'expand_recurring_events_job'...")
    admin_client = get_supabase_client()
    
    # Ambil jadwal yang perlu diproses
    # (Kita batasi 50 per siklus untuk menghindari timeout)
    schedules_to_process = await get_schedules_needing_expansion(admin_client, limit=50)
    
    if not schedules_to_process:
        logger.info("[JOB] Tidak ada jadwal yang perlu diekspansi saat ini.")
        return

    logger.info(f"[JOB] Ditemukan {len(schedules_to_process)} jadwal untuk diekspansi...")
    
    tasks = []
    for schedule in schedules_to_process:
        # Jalankan setiap ekspansi schedule sebagai task terpisah
        tasks.append(expand_and_populate_instances(schedule['schedule_id']))
        
    await asyncio.gather(*tasks)
    logger.info("[JOB] Selesai job 'expand_recurring_events_job'.")


async def cleanup_redis_busy_index_job():
    """
    [Implementasi TODO-SVC-5]
    Job harian untuk membersihkan Redis ZSET dari data lama.
    """
    logger.info("[JOB] Memulai job 'cleanup_redis_busy_index_job'...")
    try:
        # Hitung timestamp 30 hari yang lalu
        thirty_days_ago_ts = int((datetime.now(pytz.UTC) - timedelta(days=30)).timestamp())
        
        # Cari semua kunci index yang sibuk
        keys = await asyncio.to_thread(redis_client.keys, 'busy_index:*')
        
        if not keys:
            logger.info("[JOB] Tidak ada cache free/busy untuk dibersihkan.")
            return

        logger.info(f"[JOB] Membersihkan {len(keys)} cache free/busy...")
        
        def sync_redis_cleanup():
            """Bungkus panggilan blocking Redis"""
            pipe = redis_client.pipeline()
            for key in keys:
                # Hapus semua entri yang 'end_time'-nya (value)
                # lebih lama dari 30 hari yang lalu.
                # Kita asumsikan value = end_time_timestamp
                # (Perlu perbaikan jika value adalah 'schedule_id:end_time')
                
                # CATATAN: Asumsi value adalah timestamp.
                # Jika value adalah "id:timestamp", logika ini perlu diubah
                # (Lebih baik ZREMRANGEBYSCORE pada 'score' (start_time))
                
                # Logika yang lebih baik (Optimasi 5):
                # Hapus entri yang SKOR (start_time) nya lebih lama dari 30 hari lalu
                pipe.zremrangebyscore(key, 0, thirty_days_ago_ts)
            pipe.execute()

        await asyncio.to_thread(sync_redis_cleanup)
        logger.info("[JOB] Selesai membersihkan cache free/busy Redis.")
        
    except Exception as e:
        logger.error(f"[JOB] Gagal membersihkan cache Redis: {e}", exc_info=True)

async def cleanup_old_schedule_instances_job():
    """
    (Opsional) Job harian untuk menghapus data 'ScheduleInstances'
    yang sudah sangat lama (misal: > 2 bulan lalu) dari database.
    """
    logger.info("[JOB] Memulai job 'cleanup_old_schedule_instances_job'...")
    admin_client = get_supabase_client()
    
    def sync_db_call():
        try:
            two_months_ago = datetime.now(pytz.UTC) - timedelta(days=60)
            response = admin_client.table("schedule_instances") \
                .delete() \
                .lt("end_time", two_months_ago.isoformat()) \
                .execute()
            logger.info(f"[JOB] Selesai membersihkan 'ScheduleInstances' lama. {len(response.data)} baris dihapus.")
        except Exception as e:
            logger.error(f"Error cleanup_old_schedule_instances_job (sync): {e}", exc_info=True)

    try:
        await asyncio.to_thread(sync_db_call)
    except Exception as e:
        logger.error(f"Error di cleanup_old_schedule_instances_job (async): {e}", exc_info=True)