# File: backend/app/services/redis_rate_limiter.py
# (Final v3.2 - Divalidasi untuk LangGraph Checkpointer & Idempotency)

import redis.asyncio as redis
import time
import logging
from typing import Union, List, Dict, Any, Tuple
from uuid import UUID
from app.core.config import settings 
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
# --- Inisialisasi Klien Redis Async (Global) ---
# Klien ini akan dibagikan ke seluruh aplikasi
# Ini adalah klien yang akan digunakan oleh:
# 1. RedisSaver (LangGraph Checkpointer)
# 2. Idempotency Lock (ToolExecutor)
# 3. Rate Limiter (API Endpoints)
# 4. Pelacakan Pengguna Aktif (Socket)
redis_client: redis.Redis = None
try:
    logger.info(f"Mencoba menyambung ke Redis di: {settings.REDIS_URL}")
    # Buat koneksi pool
    redis_pool = redis.ConnectionPool.from_url(
        settings.REDIS_URL,
        max_connections=20,
        decode_responses=True # Penting untuk LangGraph
    )
    redis_client = redis.Redis(connection_pool=redis_pool)
    
    # Coba ping untuk memastikan koneksi
    # (Ini perlu dijalankan dalam event loop, kita pindahkan ke startup event di main.py)
except Exception as e:
    logger.critical(f"GAGAL menyambung ke Redis di {settings.REDIS_URL}: {e}")
    redis_client = None

class RedisRateLimiter:
    """
    Mengelola rate limiting dan koneksi Redis.
    """
    
    def __init__(self, client: redis.Redis = redis_client):
        self.redis = client
        self.redis_available = client is not None

    async def _is_allowed(self, key: str, limit: int, period_seconds: int) -> Tuple[bool, int]:
        """
        Logika inti rate limiting (algoritma sliding window log).
        """
        if not self.redis_available:
            return True, 0 # Gagal terbuka (fail-open) jika Redis mati

        try:
            now = int(time.time() * 1000) # Waktu dalam milidetik
            window_start = now - (period_seconds * 1000)

            async with self.safe_pipeline(self.redis, transaction=False) as pipe:
            
                # 1. Hapus log lama (di luar jendela waktu)
                pipe.zremrangebyscore(key, 0, window_start)
                # 2. Tambahkan log saat ini
                pipe.zadd(key, {str(now): now})
                # 3. Hitung jumlah log dalam jendela
                pipe.zcard(key)
                # 4. Set kadaluwarsa (expire) untuk key
                pipe.expire(key, period_seconds)
                
                results = await pipe.execute()
            
            current_count = results[2] # Hasil dari zcard
            
            if current_count > limit:
                return False, (limit - current_count) # (Mengembalikan sisa negatif)
            
            return True, (limit - current_count) # (Mengembalikan sisa)

        except Exception as e:
            logger.error(f"Error pada Redis rate limiting: {e}", exc_info=True)
            return True, 0 # Gagal terbuka (fail-open)
    

    # --- Metode Rate Limiting per Fitur ---

    async def check_guest_limit(self, guest_id: str) -> bool:
        """Limit untuk tamu (5 permintaan per 10 menit)."""
        key = f"limit:guest:{guest_id}"
        allowed, _ = await self._is_allowed(key, 5, 600)
        return allowed

    async def check_user_limit(self, user_id: UUID) -> bool:
        """Limit untuk pengguna terdaftar (100 permintaan per 10 menit)."""
        key = f"limit:user:{str(user_id)}"
        allowed, _ = await self._is_allowed(key, 100, 600)
        return allowed

    async def check_invite_limit(self, user_id: UUID) -> bool:
        """Limit undangan (5 undangan per jam)."""
        key = f"limit:invite:{str(user_id)}"
        allowed, _ = await self._is_allowed(key, 5, 3600)
        return allowed

    # --- Pelacakan Pengguna Aktif (Untuk Socket) ---

    async def add_active_user(
        self, 
        user_id: UUID, 
        canvas_id: UUID, 
        session_ttl_seconds: int = 300 
    ) -> bool:
        """
        Menambahkan user ke HSET active_users di canvas tertentu.
        """
        if not self.redis_available: return True
        
        try:
            key = f"canvas:active:{str(canvas_id)}"
            user_key = str(user_id)
            now = int(time.time())

            async with self.safe_pipeline(self.redis, transaction=False) as pipe:
                # HSET: user_id -> timestamp (untuk cleanup)
                pipe.hset(key, user_key, str(now)) 
                # EXPIRE: Set TTL untuk seluruh canvas (diperbarui setiap kali ada koneksi)
                pipe.expire(key, session_ttl_seconds) 
                await pipe.execute() 
            
            return True
        except Exception as e:
            logger.error(f"Gagal menambah active user ke Redis: {e}", exc_info=True)
            return False

    async def remove_active_user(self, user_id: UUID, canvas_id: UUID) -> bool:
        """
        Menghapus user dari daftar active_users di canvas.
        """
        if not self.redis_available: return True
        
        try:
            key = f"canvas:active:{str(canvas_id)}"
            await self.redis.hdel(key, str(user_id)) 
            return True
        except Exception as e:
            logger.error(f"Gagal menghapus active user dari Redis: {e}", exc_info=True)
            return False

    async def get_active_users_in_canvas(self, canvas_id: UUID) -> List[UUID]:
        """
        Mengambil semua user_id yang aktif di canvas.
        """
        if not self.redis_available: return []
        
        try:
            key = f"canvas:active:{str(canvas_id)}"
            # Mengambil semua field (user_id) dari HSET
            user_ids_str = await self.redis.hkeys(key) 
            return [UUID(uid) for uid in user_ids_str]
        except Exception as e:
            logger.error(f"Gagal mengambil active users dari Redis: {e}", exc_info=True)
            return []


rate_limiter = RedisRateLimiter()