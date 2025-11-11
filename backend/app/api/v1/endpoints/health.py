# File: backend/app/api/v1/endpoints/health.py

import logging
import asyncio
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status, Request, Body
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

from app.core.config import settings
from app.db.supabase_client import get_supabase_admin_async_client
import redis.asyncio as redis

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Prometheus metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

ACTIVE_WEBSOCKETS = Gauge(
    'active_websockets_total',
    'Total active WebSocket connections (estimasi dari Redis)'
)

@router.get(
    "/health",
    summary="Liveness probe"
)
async def liveness_probe():
    """
    Simple liveness probe.
    
    Returns 200 OK if the application is running.
    This endpoint doesn't check any dependencies.
    """
    return {"status": "ok"}

@router.get(
    "/ready",
    summary="Readiness probe"
)
async def readiness_probe():
    """
    Readiness probe.
    
    Returns 200 OK if the application and its dependencies are ready.
    Checks database and Redis connectivity.
    """
    # Check database connectivity
    try:
        admin_client = await get_supabase_admin_async_client()
        await admin_client.table("users").select("user_id").limit(1).execute()
    except Exception as e:
        logger.error(f"Database readiness check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not ready"
        )
    
    # Check Redis connectivity
    try:
        redis_client = redis.from_url(settings.REDIS_URL)
        await redis_client.ping()
    except Exception as e:
        logger.error(f"Redis readiness check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis is not ready"
        )
    
    return {"status": "ready"}

@router.post(
    "/debug/echo",
    summary="Echo payload for debugging"
)
async def debug_echo(
    request: Request,
    payload: Dict[str, Any] = Body(...)
):
    """
    Debug endpoint that echoes back the received payload.
    
    This endpoint is useful for testing connectivity and request handling.
    It's only available in debug mode.
    """
    # Check if debug mode is enabled
    if not getattr(settings, "DEBUG", False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint not found"
        )
    
    # Echo back the payload with additional request info
    return {
        "payload": payload,
        "headers": dict(request.headers),
        "client": {
            "host": request.client.host if request.client else None,
            "port": request.client.port if request.client else None
        }
    }

@router.get(
    "/metrics",
    summary="Prometheus metrics"
)
async def metrics():
    """
    Prometheus metrics endpoint.
    """
    
    # [REFACTOR] Menghitung koneksi dari Redis, bukan global dict
    try:
        redis_client = redis.from_url(settings.REDIS_URL)
        
        # Hitung jumlah user di semua HSET 'canvas:active:*'
        # Ini adalah operasi yang 'agak' berat, tapi lebih akurat
        total_connections = 0
        cursor = b'0'
        while True:
            cursor, keys = await redis_client.scan(cursor, match="canvas:active:*", count=100)
            if keys:
                for key in keys:
                    # HLEN mendapatkan jumlah field (user_id) di HASH
                    count = await redis_client.hlen(key)
                    total_connections += count
            if cursor == 0 or cursor == b'0':
                break
        
        ACTIVE_WEBSOCKETS.set(total_connections)
        
    except Exception as e:
        logger.warning(f"Gagal mengambil metrik koneksi aktif dari Redis: {e}")
        ACTIVE_WEBSOCKETS.set(0) # Gagal? Set ke 0
    
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

# Middleware to track metrics
async def metrics_middleware(request: Request, call_next):
    """
    Middleware to track request metrics.
    """
    import time
    
    start_time = time.time()
    
    response = await call_next(request)
    
    # Record metrics
    method = request.method
    endpoint = request.url.path
    status_code = str(response.status_code)
    
    REQUEST_COUNT.labels(
        method=method,
        endpoint=endpoint,
        status=status_code
    ).inc()
    
    REQUEST_DURATION.labels(
        method=method,
        endpoint=endpoint
    ).observe(time.time() - start_time)
    
    return response