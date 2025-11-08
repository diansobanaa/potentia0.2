# File: backend/app/services/freebusy_service.py
# (File Baru)

import logging
import asyncio
from uuid import UUID
from typing import List, Dict, Any, TYPE_CHECKING
from datetime import datetime
import pytz # Diperlukan untuk konversi timestamp

# Impor klien Redis yang sudah ada
from app.services.redis_rate_limiter import redis_client
# Impor kueri SQL fallback yang baru kita buat
from app.db.queries.calendar.calendar_queries import get_instances_for_users_in_range

if TYPE_CHECKING:
    from app.core.dependencies import AuthInfoDep

logger = logging.getLogger(__name__)

# Durasi cache untuk free/busy (10 menit)
CACHE_TTL_SECONDS = 600

class FreeBusyService:
    """
    (BARU - TODO-SVC-3)
    Service untuk menangani logika deteksi ketersediaan (free/busy).
    Menggunakan strategi 'Redis-first' untuk skalabilitas tinggi.
    """
    
    def __init__(self, auth_info: "AuthInfoDep"):
        self.user = auth_info["user"]
        self.client = auth_info["client"]
        self.redis = redis_client # Gunakan koneksi Redis yang sudah ada
        logger.debug(f"FreeBusyService diinisialisasi untuk User: {self.user.id}")

    async def get_freebusy_for_users(
        self, 
        user_ids: List[UUID],
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Mengambil data free/busy untuk daftar pengguna dalam rentang waktu.
        Mengembalikan Dict[user_id, List[busy_blocks]].
        """
        
        # Pastikan datetime adalah 'aware' (memiliki info timezone)
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=pytz.UTC)
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=pytz.UTC)

        # Ubah ke Unix timestamp (float) untuk ZSET scores
        start_ts = start_time.timestamp()
        end_ts = end_time.timestamp()
        
        results: Dict[str, List[Dict[str, Any]]] = {str(uid): [] for uid in user_ids}
        
        # --- 1. Coba Ambil dari Cache Redis ---
        users_to_fetch_from_db = []
        
        def sync_redis_check():
            """Bungkus panggilan blocking Redis"""
            pipe = self.redis.pipeline()
            for user_id in user_ids:
                key = f"busy_index:{str(user_id)}"
                # Ambil semua 'instance' di mana 'start_time' (score)
                # lebih kecil dari 'end_time' rentang
                # (Kita akan filter 'end_time' di Python)
                pipe.zrangebyscore(key, 0, end_ts)
            return pipe.execute()

        try:
            cache_results = await asyncio.to_thread(sync_redis_check)
            
            for user_id, cached_data in zip(user_ids, cache_results):
                user_id_str = str(user_id)
                if not cached_data:
                    # Cache Miss: Pengguna ini perlu diambil dari DB
                    users_to_fetch_from_db.append(user_id)
                    continue
                
                # Cache Hit: Proses data dari Redis
                busy_blocks = []
                for item in cached_data:
                    try:
                        # Asumsi value = "schedule_id:end_time_timestamp"
                        # (Ini perlu disamakan dengan job ekspansi)
                        # Untuk sekarang, kita asumsikan value = end_time_timestamp (float)
                        item_end_ts = float(item)
                        
                        # Cek overlap: (item.start < R.end) AND (item.end > R.start)
                        # 'zrangebyscore' sudah menangani (item.start < R.end)
                        if item_end_ts > start_ts:
                            # (Kita tidak tahu start_time dari value ini,
                            #  ini adalah kelemahan desain Redis ZSET saya)
                            # ---
                            # PIVOT LOGIKA (Lebih Baik):
                            # Skor = start_time_ts
                            # Value = end_time_ts
                            # Kueri: ZRANGEBYSCORE key 0 end_ts
                            #
                            # Mari kita asumsikan Job kita menyimpan:
                            # Skor = start_time_ts
                            # Value = end_time_ts
                            # (Saya akan perbaiki job 'cleanup' agar cocok dengan ini)
                            
                            # (Perbaikan Logika Cache - ZSET value adalah string)
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
            logger.warning(f"Gagal memeriksa cache Redis: {e}. Mengambil semua dari DB.", exc_info=True)
            users_to_fetch_from_db = user_ids # Ambil semua jika Redis gagal
            results = {str(uid): [] for uid in user_ids} # Reset hasil

        # --- 2. Fallback: Ambil dari Database (SQL) ---
        if users_to_fetch_from_db:
            logger.info(f"Cache miss. Mengambil data free/busy dari DB untuk {len(users_to_fetch_from_db)} pengguna.")
            
            db_instances = await get_instances_for_users_in_range(
                self.client, users_to_fetch_from_db, start_time, end_time
            )
            
            # Siapkan data untuk cache Redis
            redis_pipe = self.redis.pipeline()
            
            for instance in db_instances:
                uid_str = str(instance['user_id'])
                
                # Konversi ke timestamp untuk Redis
                inst_start_ts = instance['start_time'].timestamp()
                inst_end_ts = instance['end_time'].timestamp()
                
                # Tambahkan ke hasil respons
                results[uid_str].append({
                    "user_id": uid_str,
                    "start_time": instance['start_time'].isoformat(),
                    "end_time": instance['end_time'].isoformat()
                })
                
                # Tambahkan ke pipeline cache
                key = f"busy_index:{uid_str}"
                # Skor = start_time
                # Value = "start_time:end_time" (untuk overlap check)
                value = f"{inst_start_ts}:{inst_end_ts}"
                redis_pipe.zadd(key, {value: inst_start_ts})
            
            # Set TTL untuk semua kunci yang baru diisi
            for user_id in users_to_fetch_from_db:
                redis_pipe.expire(f"busy_index:{str(user_id)}", CACHE_TTL_SECONDS)
                
            # Jalankan pipeline Redis di thread
            await asyncio.to_thread(redis_pipe.execute)
            logger.info(f"Cache Redis berhasil diisi ulang untuk {len(users_to_fetch_from_db)} pengguna.")

        return results