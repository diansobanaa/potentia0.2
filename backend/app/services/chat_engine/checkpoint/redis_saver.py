import logging
import asyncio
from typing import Any, Optional

from langchain_core.load.dump import dumps as lc_dumps
from langchain_core.load.load import loads as lc_loads
from langgraph.checkpoint.redis import RedisSaver as OldRedisSaver
from langgraph.checkpoint.base import CheckpointTuple
from langchain_core.runnables import RunnableConfig

logger = logging.getLogger(__name__)


class LangChainSerializer:
    """Serializer kustom kompatibel LangGraph terbaru."""

    def dumps(self, obj: Any) -> bytes:
        """Serialize obyek Python menjadi bytes JSON."""
        import json
        try:
            return lc_dumps(obj).encode("utf-8")
        except Exception:
            return json.dumps(obj, default=str).encode("utf-8")

    def loads(self, data: bytes) -> Any:
        """Deserialize bytes JSON menjadi obyek Python."""
        import json
        s = data.decode("utf-8")
        try:
            return lc_loads(s)
        except Exception:
            return json.loads(s)

    def dumps_typed(self, obj: Any) -> tuple[str, bytes]:
        """Dikonsumsi oleh LangGraph RedisSaver."""
        type_name = obj.__class__.__name__ if obj is not None else "NoneType"
        return type_name, self.dumps(obj)

    def loads_typed(self, type_name: str, data: bytes) -> Any:
        """Lawan dari dumps_typed()."""
        return self.loads(data)


class AsyncCompatibleRedisSaver(OldRedisSaver):
    """
    Wrapper untuk OldRedisSaver dengan async support.
    
    FIX: Menggunakan sync Redis client untuk kompatibilitas dengan redisvl pipeline.
    """
    
    def __init__(self, redis_client, *args, **kwargs):
        """
        Initialize dengan sync Redis client.
        
        Args:
            redis_client: Async redis client (akan dikonversi ke sync)
        """
        logger.info(f"DEBUG: Menginisialisasi RedisSaver...")
        logger.info(f"DEBUG: Tipe redis_client yang diterima: {type(redis_client)}")
        
        # FIX: Konversi async client ke sync client
        sync_redis_client = self._get_sync_redis_client(redis_client)
        
        # Pass sync client ke parent
        kwargs['redis_client'] = sync_redis_client
        super().__init__(*args, **kwargs)
        
        # Override serializer
        self.serde = LangChainSerializer()
    
    def _get_sync_redis_client(self, async_client):
        """
        Membuat sync Redis client dari connection info async client.
        
        Args:
            async_client: redis.asyncio.Redis instance
            
        Returns:
            redis.Redis: Sync Redis client
        """
        try:
            # Import sync Redis
            import redis
            
            # Extract connection info dari async client
            connection_kwargs = async_client.connection_pool.connection_kwargs.copy()
            
            # Hapus kwargs yang tidak kompatibel dengan sync client
            connection_kwargs.pop('loop', None)
            connection_kwargs.pop('connection_class', None)
            
            # Buat sync client dengan connection info yang sama
            sync_client = redis.Redis(**connection_kwargs)
            
            logger.info(f"DEBUG: Berhasil membuat sync Redis client dari async client")
            return sync_client
            
        except Exception as e:
            logger.error(f"DEBUG: Gagal membuat sync client: {e}")
            # Fallback: buat client baru dengan default settings
            import redis
            import os
            
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            sync_client = redis.from_url(redis_url, decode_responses=False)
            logger.warning(f"DEBUG: Menggunakan fallback sync client dari REDIS_URL")
            return sync_client

    # === EXISTING ASYNC METHODS ===
    async def aget_tuple(self, config: RunnableConfig, *args, **kwargs) -> Optional[CheckpointTuple]:
        return await asyncio.to_thread(self.get_tuple, config, *args, **kwargs)

    async def aput_tuple(self, config: RunnableConfig, checkpoint: CheckpointTuple, *args, **kwargs) -> None:
        await asyncio.to_thread(self.put_tuple, config, checkpoint, *args, **kwargs)

    async def aget(self, config: RunnableConfig, *args, **kwargs) -> Optional[dict]:
        return await asyncio.to_thread(self.get, config, *args, **kwargs)

    async def aput(self, config: RunnableConfig, checkpoint: dict, *args, **kwargs) -> None:
        await asyncio.to_thread(self.put, config, checkpoint, *args, **kwargs)
    
    # === NEW: MISSING ASYNC METHODS ===
    
    async def aput_writes(self, config: RunnableConfig, writes: list, task_id: str) -> None:
        """
        Async wrapper untuk put_writes.
        Dipanggil oleh LangGraph untuk menyimpan intermediate writes.
        """
        return await asyncio.to_thread(self.put_writes, config, writes, task_id)
    
    async def alist(self, config: RunnableConfig, **kwargs):
        """
        Async wrapper untuk list checkpoints.
        """
        # Sync version returns generator, convert to list first
        def _sync_list():
            return list(self.list(config, **kwargs))
        
        items = await asyncio.to_thread(_sync_list)
        # Return async generator
        for item in items:
            yield item
    
    async def asearch(self, **kwargs):
        """
        Async wrapper untuk search operation (jika diperlukan).
        """
        def _sync_search():
            return list(self.search(**kwargs))
        
        items = await asyncio.to_thread(_sync_search)
        for item in items:
            yield item
