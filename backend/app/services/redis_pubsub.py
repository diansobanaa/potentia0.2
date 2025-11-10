# File: backend/app/services/redis_pubsub.py
# (FILE BARU)

import logging
import asyncio
import json
from typing import AsyncGenerator, Dict, Any
import redis.asyncio as redis
from redis.asyncio.client import PubSub

from app.core.config import settings #

logger = logging.getLogger(__name__)

class RedisPubSubManager:
    """
    Mengelola koneksi Redis Pub/Sub untuk real-time broadcast.
    """
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.publisher = None
        self.subscriber = None

    async def connect(self):
        """Membangun koneksi publisher dan subscriber."""
        try:
            self.publisher = redis.from_url(self.redis_url)
            self.subscriber = redis.from_url(self.redis_url)
            await self.publisher.ping()
            await self.subscriber.ping()
            logger.info("Koneksi Redis Pub/Sub berhasil dibuat.")
        except Exception as e:
            logger.critical(f"Gagal terhubung ke Redis Pub/Sub: {e}", exc_info=True)
            self.publisher = None
            self.subscriber = None

    async def publish(self, channel: str, message: Dict[str, Any]):
        """Mem-publish pesan JSON ke channel Redis."""
        if not self.publisher:
            logger.warning("Publisher Redis tidak terinisialisasi. Mencoba koneksi ulang...")
            await self.connect()
            if not self.publisher:
                logger.error("Gagal mem-publish, koneksi Redis tidak ada.")
                return

        try:
            await self.publisher.publish(channel, json.dumps(message))
        except Exception as e:
            logger.error(f"Gagal publish ke channel {channel}: {e}", exc_info=True)

    async def subscribe(self, channel: str) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Men-subscribe ke channel dan menghasilkan (yield) pesan yang masuk.
        """
        if not self.subscriber:
            logger.error("Subscriber Redis tidak ada. Tidak bisa subscribe.")
            return

        pubsub: PubSub = self.subscriber.pubsub()
        await pubsub.subscribe(channel)
        
        logger.info(f"Berhasil subscribe ke channel: {channel}")
        
        try:
            async for message in pubsub.listen():
                if message.get("type") == "message":
                    try:
                        data = json.loads(message.get("data", "{}"))
                        yield data
                    except json.JSONDecodeError:
                        logger.warning(f"Menerima pesan non-JSON di channel {channel}")
        except asyncio.CancelledError:
            logger.info(f"Unsubscribing dari channel {channel} (CancelledError)")
        except Exception as e:
            logger.error(f"Error saat listening ke channel {channel}: {e}", exc_info=True)
        finally:
            logger.info(f"Proses subscribe ke {channel} berhenti.")
            await pubsub.unsubscribe(channel)
            await pubsub.close()

# Buat instance singleton untuk digunakan di seluruh aplikasi
redis_pubsub_manager = RedisPubSubManager(settings.REDIS_URL)

# Event handler untuk startup dan shutdown FastAPI
async def connect_redis_pubsub():
    await redis_pubsub_manager.connect()

async def disconnect_redis_pubsub():
    if redis_pubsub_manager.publisher:
        await redis_pubsub_manager.publisher.close()
    if redis_pubsub_manager.subscriber:
        await redis_pubsub_manager.subscriber.close()
    logger.info("Koneksi Redis Pub/Sub ditutup.")