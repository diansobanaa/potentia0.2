# File: backend/app/services/calendar/freebusy_service.py
# (Diperbarui untuk klien Redis async native)

import logging
import asyncio
from uuid import UUID
from typing import List, Dict, Any, TYPE_CHECKING
from datetime import datetime
import pytz 

# --- PERBAIKAN: Impor klien Redis async ---
from app.services.redis_rate_limiter import redis_client
# ----------------------------------------
from app.db.queries.calendar.calendar_queries import get_instances_for_users_in_range

if TYPE_CHECKING:
    from app.core.dependencies import AuthInfoDep

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 600

class FreeBusyService:
    def __init__(self, auth_info: "AuthInfoDep"):
        self.user = auth_info["user"]
        self.client = auth_info["client"] # Ini sekarang AsyncClient
        self.redis = redis_client # Ini sekarang Async Redis Client
        logger.debug(f"FreeBusyService (Async) diinisialisasi untuk User: {self.user.id}")

    async def get_freebusy_for_users(
        self, 
        user_ids: List[UUID],
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, List[Dict[str, Any]]]:
        
        if start_time.tzinfo is None: start_time = start_time.replace(tzinfo=pytz.UTC)
        if end_time.tzinfo is None: end_time = end_time.replace(tzinfo=pytz.UTC)

        start_ts = start_time.timestamp()
        end_ts = end_time.timestamp()
        
        results: Dict[str, List[Dict[str, Any]]] = {str(uid): [] for uid in user_ids}
        users_to_fetch_from_db = []
        
        # --- 1. Coba Ambil dari Cache Redis (Async Native) ---
        try:
            # --- PERBAIKAN: Gunakan pipeline async ---
            async with self.redis.pipeline() as pipe:
                for user_id in user_ids:
                    key = f"busy_index:{str(user_id)}"
                    # (Asumsi Skor = start_time, Value = "start:end")
                    pipe.zrangebyscore(key, 0, end_ts)
                cache_results = await pipe.execute()
            # ----------------------------------------
            
            for user_id, cached_data in zip(user_ids, cache_results):
                user_id_str = str(user_id)
                if not cached_data:
                    users_to_fetch_from_db.append(user_id)
                    continue
                
                busy_blocks = []
                for item in cached_data: # item adalah "start_ts:end_ts"
                    try:
                        item_start_ts_str, item_end_ts_str = item.split(':')
                        item_start_ts = float(item_start_ts_str)
                        item_end_ts = float(item_end_ts_str)

                        if item_end_ts > start_ts: # Cek overlap
                            busy_blocks.append({
                                "user_id": user_id_str,
                                "start_time": datetime.fromtimestamp(item_start_ts, tz=pytz.UTC).isoformat(),
                                "end_time": datetime.fromtimestamp(item_end_ts, tz=pytz.UTC).isoformat()
                            })
                    except Exception:
                        pass # Abaikan item cache yang rusak
                
                results[user_id_str] = busy_blocks

        except Exception as e:
            logger.warning(f"Gagal memeriksa cache Redis (async): {e}. Mengambil semua dari DB.", exc_info=True)
            users_to_fetch_from_db = user_ids
            results = {str(uid): [] for uid in user_ids}

        # --- 2. Fallback: Ambil dari Database (Async Native) ---
        if users_to_fetch_from_db:
            logger.info(f"Cache miss. Mengambil data free/busy dari DB (async) untuk {len(users_to_fetch_from_db)} pengguna.")
            
            # Panggilan kueri sekarang async native
            db_instances = await get_instances_for_users_in_range(
                self.client, users_to_fetch_from_db, start_time, end_time
            )
            
            # --- PERBAIKAN: Gunakan pipeline async ---
            async with self.redis.pipeline() as redis_pipe:
                for instance in db_instances:
                    uid_str = str(instance['user_id'])
                    inst_start_ts = instance['start_time'].timestamp()
                    inst_end_ts = instance['end_time'].timestamp()
                    
                    results[uid_str].append({
                        "user_id": uid_str,
                        "start_time": instance['start_time'].isoformat(),
                        "end_time": instance['end_time'].isoformat()
                    })
                    
                    key = f"busy_index:{uid_str}"
                    value = f"{inst_start_ts}:{inst_end_ts}"
                    redis_pipe.zadd(key, {value: inst_start_ts})
                
                for user_id in users_to_fetch_from_db:
                    redis_pipe.expire(f"busy_index:{str(user_id)}", CACHE_TTL_SECONDS)
                    
                # Jalankan pipeline Redis async
                await redis_pipe.execute()
            # ----------------------------------------
            logger.info(f"Cache Redis (async) berhasil diisi ulang untuk {len(users_to_fetch_from_db)} pengguna.")

        return results