import redis
import os
import time
from typing import Union
from uuid import UUID

# Koneksi ke Redis
redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"), decode_responses=True)

class RedisRateLimiter:
    def __init__(self):
        self.redis = redis_client

    def _is_allowed(self, key: str, limit: int, window_seconds: int) -> bool:
        """
        Menggunakan algoritma sliding window dengan Redis.
        """
        pipe = self.redis.pipeline()
        now = int(time.time())
        
        # Hapus entri yang sudah kedaluwarsa
        pipe.zremrangebyscore(key, 0, now - window_seconds)
        # Hitung jumlah entri dalam jendela waktu
        pipe.zcard(key)
        # Tambahkan request saat ini
        pipe.zadd(key, {str(now): now})
        # Set agar key kedaluwarsa
        pipe.expire(key, window_seconds)
        
        results = pipe.execute()
        current_requests = results[1]
        
        return current_requests < limit

    def check_guest_limit(self, ip_address: str) -> bool:
        return self._is_allowed(f"guest_limit:{ip_address}", limit=10, window_seconds=3600)

    def check_user_limit(self, user_id: Union[UUID, str], tier: str) -> bool:
        if tier in ['pro', 'admin']:
            return True
        return self._is_allowed(f"user_limit:{str(user_id)}", limit=100, window_seconds=3600)

rate_limiter = RedisRateLimiter()