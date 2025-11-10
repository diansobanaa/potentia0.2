# File: backend/app/jobs/schedule_expander.py
# (Diperbarui untuk klien DB & Redis async native)

import logging
import asyncio
from uuid import UUID
from datetime import datetime, timedelta
from typing import List, Dict, Any, Set, Tuple
from dateutil.rrule import rrule, rrulestr, rruleset
from dateutil.parser import parse as dt_parse
import pytz 

# --- PERBAIKAN: Impor klien DB dan Redis async ---
from app.db.supabase_client import get_supabase_admin_async_client
from app.services.redis_rate_limiter import rate_limiter # (Sekarang async)
# ---------------------------------------------------

# Impor Kueri (sekarang semuanya async)
from app.db.queries.calendar.calendar_queries import (
    get_calendar_subscribers,
    get_schedules_needing_expansion,
    bulk_delete_instances_for_schedule,
    bulk_insert_instances,
    get_schedule_by_id # <-- [DITAMBAHKAN]
)
from app.core.exceptions import DatabaseError

logger = logging.getLogger(__name__)

EXPANSION_LOCK_TTL = 300 # 5 menit TTL untuk lock

# (_generate_timestamps tidak berubah)
def _generate_timestamps(
    schedule: Dict[str, Any],
    start_range: datetime,
    end_range: datetime
) -> List[Tuple[datetime, datetime]]:
    # ... (logika tidak berubah) ...
    instances = []
    if schedule['start_time'].tzinfo is None: schedule['start_time'] = schedule['start_time'].replace(tzinfo=pytz.UTC)
    if schedule['end_time'].tzinfo is None: schedule['end_time'] = schedule['end_time'].replace(tzinfo=pytz.UTC)
    duration = schedule['end_time'] - schedule['start_time']
    ruleset = rruleset()
    if schedule.get('rrule'): ruleset.rrule(rrulestr(schedule['rrule'], dtstart=schedule['start_time']))
    if schedule.get('rdate'):
        for rdate_str in schedule['rdate']:
            try: ruleset.rdate(dt_parse(rdate_str).replace(tzinfo=pytz.UTC))
            except Exception: pass 
    if schedule.get('exdate'):
        for exdate_str in schedule['exdate']:
            try: ruleset.exdate(dt_parse(exdate_str).replace(tzinfo=pytz.UTC))
            except Exception: pass
    try:
        for dt_start in ruleset.between(start_range, end_range):
            dt_end = dt_start + duration
            instances.append((dt_start, dt_end))
    except Exception as e:
         logger.error(f"Gagal ekspansi rrule untuk schedule {schedule['schedule_id']}: {e}", exc_info=True)
    if not schedule.get('rrule'):
        if schedule['start_time'] <= end_range and schedule['end_time'] >= start_range:
            instances.append((schedule['start_time'], schedule['end_time']))
    return instances


async def expand_and_populate_instances(schedule_id: UUID):
    """
    [PERBAIKAN] Ekspansi RRULE Async Penuh (DB & Redis).
    """
    
    # --- PERBAIKAN: Panggil Redis async ---
    lock_key = f"lock:expand:{str(schedule_id)}"
    is_locked = await rate_limiter.set(
        lock_key, "running", ex=EXPANSION_LOCK_TTL, nx=True
    )
    
    if not is_locked:
        logger.warning(f"[JOB] Melewatkan ekspansi untuk {schedule_id}, job lain sedang berjalan (lock aktif).")
        return
    # -----------------------------------

    logger.info(f"[JOB] Memulai ekspansi (lock diperoleh) untuk schedule_id: {schedule_id}")
    
    # --- PERBAIKAN: Dapatkan klien DB async ---
    admin_client = get_supabase_admin_async_client()
    
    try:
        # Panggil kueri async native
        schedule = await get_schedule_by_id(admin_client, schedule_id)
        
        if not schedule:
            logger.error(f"[JOB] Gagal ekspansi: Schedule {schedule_id} tidak ditemukan.")
            return

        calendar_id = schedule.get('calendar_id')
        
        # Panggil kueri async native
        subscribers = await get_calendar_subscribers(admin_client, calendar_id)
        if not subscribers:
            logger.warning(f"[JOB] Melewatkan schedule {schedule_id}, tidak ada subscriber.")
            return

        user_ids_affected: Set[UUID] = set()
        for user_sub in subscribers:
            if user_sub.get('user_id'):
                user_ids_affected.add(UUID(user_sub.get('user_id')))

        # (Logika _generate_timestamps tidak berubah)
        now = datetime.now(pytz.UTC)
        start_range = now - timedelta(days=30) 
        end_range = now + timedelta(days=730)
        
        if schedule.get('is_deleted', False):
            instances_timestamps = []
        else:
            instances_timestamps = _generate_timestamps(schedule, start_range, end_range)

        instances_batch = []
        if instances_timestamps:
            for user_id in user_ids_affected:
                for dt_start, dt_end in instances_timestamps:
                    instances_batch.append({
                        "schedule_id": str(schedule_id),
                        "calendar_id": str(calendar_id),
                        "user_id": str(user_id),
                        "start_time": dt_start.isoformat(),
                        "end_time": dt_end.isoformat(),
                        "is_exception": False
                    })

        # Panggil kueri async native
        logger.debug(f"[JOB] Menghapus instance lama untuk {schedule_id}...")
        await bulk_delete_instances_for_schedule(admin_client, schedule_id)

        if instances_batch:
            logger.info(f"[JOB] Menyisipkan {len(instances_batch)} instance baru untuk {schedule_id}.")
            # Panggil kueri async native
            await bulk_insert_instances(admin_client, instances_batch)
        
        if user_ids_affected:
            logger.info(f"[JOB] Meng-invalidasi cache free/busy (async) untuk {len(user_ids_affected)} pengguna...")
            redis_keys_to_delete = [f"busy_index:{str(uid)}" for uid in user_ids_affected]
            # --- PERBAIKAN: Panggil Redis async ---
            if redis_keys_to_delete:
                await rate_limiter.delete(*redis_keys_to_delete)

    except Exception as e:
        logger.error(f"[JOB] Gagal total saat ekspansi schedule {schedule_id}: {e}", exc_info=True)
    
    finally:
        # --- PERBAIKAN: Panggil Redis async ---
        logger.info(f"[JOB] Ekspansi selesai. Melepaskan lock untuk {schedule_id}.")
        await rate_limiter.delete(lock_key)


async def expand_recurring_events_job():
    logger.info("[JOB] Memulai job 'expand_recurring_events_job'...")
    
    # --- PERBAIKAN: Panggil Redis async ---
    lock_key = "lock:expand_recurring_events_job"
    is_locked = await rate_limiter.redis.set(
        lock_key, "1", nx=True, ex=300
    )
    if not is_locked:
        logger.warning("[JOB] Melewatkan 'expand_recurring_events_job', job lain sedang berjalan (lock global aktif).")
        return
    # -----------------------------------
    
    admin_client = get_supabase_admin_async_client()
    try:
        # Panggil kueri async native
        schedules_to_process = await get_schedules_needing_expansion(admin_client, limit=50)
        
        if not schedules_to_process:
            logger.info("[JOB] Tidak ada jadwal yang perlu diekspansi saat ini.")
            return

        tasks = []
        for schedule in schedules_to_process:
            tasks.append(expand_and_populate_instances(schedule['schedule_id']))
            
        await asyncio.gather(*tasks)
        logger.info("[JOB] Selesai job 'expand_recurring_events_job'.")
    
    except Exception as e:
         logger.error(f"[JOB] Error di 'expand_recurring_events_job' (loop utama): {e}", exc_info=True)
    finally:
        # --- PERBAIKAN: Panggil Redis async ---
        await rate_limiter.delete(lock_key)


async def cleanup_redis_busy_index_job():
    logger.info("[JOB] Memulai job 'cleanup_redis_busy_index_job'...")
    try:
        thirty_days_ago_ts = int((datetime.now(pytz.UTC) - timedelta(days=30)).timestamp())
        
        # --- PERBAIKAN: Panggil Redis async ---
        keys = await rate_limiter.keys('busy_index:*')
        
        if not keys:
            logger.info("[JOB] Tidak ada cache free/busy untuk dibersihkan.")
            return

        logger.info(f"[JOB] Membersihkan {len(keys)} cache free/busy (async)...")
        
        async with rate_limiter.pipeline() as pipe:
            for key in keys:
                pipe.zremrangebyscore(key, 0, thirty_days_ago_ts)
            await pipe.execute()
        # -----------------------------------
            
        logger.info("[JOB] Selesai membersihkan cache free/busy Redis.")
        
    except Exception as e:
        logger.error(f"[JOB] Gagal membersihkan cache Redis (async): {e}", exc_info=True)

async def cleanup_old_schedule_instances_job():
    logger.info("[JOB] Memulai job 'cleanup_old_schedule_instances_job'...")
    admin_client = get_supabase_admin_async_client()
    
    try:
        two_months_ago = datetime.now(pytz.UTC) - timedelta(days=60)
        # --- PERBAIKAN: Panggil DB async native ---
        response = await admin_client.table("schedule_instances") \
            .delete() \
            .lt("end_time", two_months_ago.isoformat()) \
            .execute()
        logger.info(f"[JOB] Selesai membersihkan 'ScheduleInstances' lama. {len(response.data)} baris dihapus.")
    except Exception as e:
        logger.error(f"Error cleanup_old_schedule_instances_job (async): {e}", exc_info=True)