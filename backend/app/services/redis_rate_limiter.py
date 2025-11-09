# backend/app/services/redis_rate_limiter.py
# (Diperbarui untuk redis.asyncio)

# --- PERBAIKAN: Impor redis.asyncio ---
import redis.asyncio as redis
import time
import logging
from typing import Union
from uuid import UUID
from app.core.config import settings  # <-- [DITAMBAHKAN] Impor settings

logger = logging.getLogger(__name__)

# --- PERBAIKAN: Gunakan 'from_url' dari klien async ---
try:
    redis_client = redis.from_url(
        settings.REDIS_URL, decode_responses=True
    )
except Exception as e:
    logger.warning(
        f"Gagal membuat Redis client: {e}. "
        "Rate limiting akan dinonaktifkan."
    )
    redis_client = None


class RedisRateLimiter:
    def __init__(self):
        self.redis = redis_client
        self.redis_available = redis_client is not None

    # --- PERBAIKAN: Ubah menjadi 'async def' ---
    async def _is_allowed(
        self, key: str, limit: int, window_seconds: int
    ) -> bool:
        """
        Menggunakan algoritma sliding window dengan Redis (Async).

        Jika Redis tidak tersedia, return True (allow request)
        untuk graceful degradation.
        """
        # Graceful degradation: jika Redis tidak tersedia, allow request
        if not self.redis_available or not self.redis:
            logger.debug(
                f"Redis tidak tersedia, melewati rate limit check untuk {key}"
            )
            return True

        try:
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
        except redis.ConnectionError as e:
            logger.warning(
                f"Redis connection error: {e}. "
                "Melewati rate limit check (allow request)."
            )
            # Graceful degradation: allow request jika Redis error
            return True
        except Exception as e:
            logger.error(
                f"Error saat check rate limit untuk {key}: {e}",
                exc_info=True
            )
            # Graceful degradation: allow request jika error
            return True

    # --- PERBAIKAN: Ubah menjadi 'async def' ---
    async def check_guest_limit(self, ip_address: str) -> bool:
        return await self._is_allowed(
            f"guest_limit:{ip_address}",
            limit=10,
            window_seconds=3600
        )

    # --- PERBAIKAN: Ubah menjadi 'async def' ---
    async def check_user_limit(
        self, user_id: Union[UUID, str], tier: str
    ) -> bool:
        if tier in ['pro', 'admin']:
            return True
        return await self._is_allowed(
            f"user_limit:{str(user_id)}",
            limit=100,
            window_seconds=3600
        )

    # --- [BARU] Rate limiting untuk workspace invitations ---
    async def check_invite_limit_per_user(
        self,
        user_id: Union[UUID, str],
        limit: int = 50,
        window_seconds: int = 3600
    ) -> bool:
        """
        Memeriksa apakah user (admin) dapat mengirim undangan lebih banyak.

        Batas default: 50 undangan per jam per user.
        Ini mencegah admin mengirim terlalu banyak undangan.
        """
        return await self._is_allowed(
            f"invite_limit:user:{str(user_id)}",
            limit=limit,
            window_seconds=window_seconds
        )

    async def check_invite_limit_per_workspace(
        self,
        workspace_id: Union[UUID, str],
        limit: int = 100,
        window_seconds: int = 3600
    ) -> bool:
        """
        Memeriksa apakah workspace dapat mengirim undangan lebih banyak.

        Batas default: 100 undangan per jam per workspace.
        Ini mencegah satu workspace mengirim terlalu banyak
        undangan secara keseluruhan.
        """
        return await self._is_allowed(
            f"invite_limit:workspace:{str(workspace_id)}",
            limit=limit,
            window_seconds=window_seconds
        )

    async def check_invite_limit_per_email(
        self,
        email: str,
        limit: int = 5,
        window_seconds: int = 3600
    ) -> bool:
        """
        Memeriksa apakah email tertentu dapat menerima undangan lebih banyak.

        Batas default: 5 undangan per jam per email.
        Ini mencegah spam/harassment ke email tertentu.

        Note: Email dinormalisasi menjadi lowercase untuk konsistensi.
        """
        normalized_email = email.lower().strip()
        return await self._is_allowed(
            f"invite_limit:email:{normalized_email}",
            limit=limit,
            window_seconds=window_seconds
        )


rate_limiter = RedisRateLimiter()
