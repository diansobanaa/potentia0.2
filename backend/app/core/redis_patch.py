# File: app/core/redis_patch.py
# Tujuan: Menambahkan dukungan context manager ke redis.client.Pipeline
# agar kompatibel dengan redisvl & langgraph-checkpoint-redis

import redis
from redis.client import Pipeline

if not hasattr(Pipeline, "__enter__"):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.close()
        except Exception:
            pass

    Pipeline.__enter__ = __enter__
    Pipeline.__exit__ = __exit__
    print("[RedisPatch] Pipeline context manager successfully patched.")