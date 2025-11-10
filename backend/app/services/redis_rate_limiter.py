# backend/app/services/redis_rate_limiter.py
# (Diperbarui untuk redis.asyncio dan Task 3)

import redis.asyncio as redis
import time
import logging
from typing import Union, List, Dict, Any, Tuple
from uuid import UUID
from app.core.config import settings  
from datetime import datetime, timedelta # DITAMBAHKAN

logger = logging.getLogger(__name__)

# ... (Logika inisialisasi redis_client)

class RedisRateLimiter:
    # ... (Logika __init__ dan _is_allowed tidak berubah)

    # ... (Logika check_guest_limit, check_user_limit, check_invite_limit tidak berubah)

    # --- [BARU] Pelacakan Pengguna Aktif (Task 3) ---
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

            async with self.redis.pipeline() as pipe:
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