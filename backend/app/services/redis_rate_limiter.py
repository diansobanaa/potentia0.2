# backend/app/services/redis_rate_limiter.py
# (Diperbarui untuk redis.asyncio)

# --- PERBAIKAN: Impor redis.asyncio ---
import redis.asyncio as redis
import os
import time
from typing import Union
from uuid import UUID
from app.core.config import settings # <-- [DITAMBAHKAN] Impor settings

# --- PERBAIKAN: Gunakan 'from_url' dari klien async ---
redis_client = redis.from_url(
    settings.REDIS_URL, decode_responses=True
)

class RedisRateLimiter:
    def __init__(self):
        self.redis = redis_client

    # --- PERBAIKAN: Ubah menjadi 'async def' ---
    async def _is_allowed(self, key: str, limit: int, window_seconds: int) -> bool:
        """
        Menggunakan algoritma sliding window dengan Redis (Async).
        """
        # --- PERBAIKAN: Gunakan 'async with' untuk pipeline ---
        async with self.redis.pipeline() as pipe:
            now = int(time.time())
            
            # Hapus entri yang sudah kedaluwarsa
            pipe.zremrangebyscore(key, 0, now - window_seconds)
            # Hitung jumlah entri dalam jendela waktu
            pipe.zcard(key)
            # Tambahkan request saat ini
            pipe.zadd(key, {str(now): now})
            # Set agar key kedaluwarsa
            pipe.expire(key, window_seconds)
            
            # --- PERBAIKAN: Gunakan 'await' ---
            results = await pipe.execute()
            current_requests = results[1]
            
            return current_requests < limit

    # --- PERBAIKAN: Ubah menjadi 'async def' ---
    async def check_guest_limit(self, ip_address: str) -> bool:
        return await self._is_allowed(f"guest_limit:{ip_address}", limit=10, window_seconds=3600)

    # --- PERBAIKAN: Ubah menjadi 'async def' ---
    async def check_user_limit(self, user_id: Union[UUID, str], tier: str) -> bool:
        if tier in ['pro', 'admin']:
            return True
        return await self._is_allowed(f"user_limit:{str(user_id)}", limit=100, window_seconds=3600)

rate_limiter = RedisRateLimiter()