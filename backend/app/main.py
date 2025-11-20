# File: backend/app/main.py
# (Diperbaiki: Impor OTEL dan Handler Lifespan)
import app.core.redis_patch # Patch Redis AsyncIO sebelum impor lainnya
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
import sys
from app.api.v1.api import api_router
from app.api.v1.endpoints.health import metrics_middleware
from app.core.config import settings
import logging.config
from app.services.chat_engine.schemas import PaginatedConversationListResponse
from app.core.scheduler import scheduler, setup_scheduler_jobs #

# --- [TAMBAHAN] Impor Handler Startup/Shutdown ---
from app.db.asyncpg_pool import create_asyncpg_pool, close_asyncpg_pool
from app.services.redis_pubsub import connect_redis_pubsub, disconnect_redis_pubsub
from app.workers.embedding import stop_embedding_worker
from app.workers.rebalance import stop_rebalance_worker
from app.workers.cleanup import stop_cleanup_worker


# --- OpenTelemetry Setup ---
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
# [PERBAIKAN] Impor 'Resource' yang hilang
from opentelemetry.sdk.resources import Resource, OTEL_RESOURCE_ATTRIBUTES
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def setup_opentelemetry(app: FastAPI): # [REKOMENDASI] Kirim 'app' ke fungsi
    """Configure OpenTelemetry tracing."""
    if not settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        logger.warning("OpenTelemetry endpoint not configured. Skipping tracing setup.")
        return

    resource = Resource(attributes={
        OTEL_RESOURCE_ATTRIBUTES["SERVICE_NAME"]: "potentia-api",
        OTEL_RESOURCE_ATTRIBUTES["SERVICE_VERSION"]: "0.4.3",
    })

    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)

    otlp_exporter = OTLPSpanExporter(
        endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
        insecure=True # Set to False for production with TLS
    )

    span_processor = BatchSpanProcessor(otlp_exporter)
    tracer_provider.add_span_processor(span_processor)

    # Instrument FastAPI and httpx
    FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)
    HTTPXClientInstrumentor.instrument()

    logger.info("OpenTelemetry configured successfully.")
# --- KONFIGURASI LOGGING (Tidak berubah) ---
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": sys.stdout,
        },
    },
    "loggers": {
        "": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "app": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "httpx": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "httpcore": {
             "handlers": ["console"],
             "level": "INFO",
             "propagate": False,
         },
        "hpack": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
         "google.api_core": {
             "handlers": ["console"],
             "level": "INFO",
             "propagate": False,
         },
         "google.auth": {
             "handlers": ["console"],
             "level": "INFO",
             "propagate": False,
         },
         "uvicorn": {
             "handlers": ["console"],
             "level": "INFO",
             "propagate": False,
         },
         "uvicorn.error": {
             "level": "INFO",
              "propagate": False,
         },
         "uvicorn.access": {
             "handlers": ["console"],
             "level": "INFO",
             "propagate": False,
         },
    },
}

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger("app")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    [DIREFACTOR] Mengelola siklus hidup koneksi dan worker.
    """
    logger.info("Aplikasi FastAPI memulai startup...")
    
    # --- STARTUP ---
    try:
        # 1. Hubungkan Koneksi Eksternal
        await connect_redis_pubsub()  # Untuk WebSocket & SSE scaling
        await create_asyncpg_pool()   # Untuk RebalanceWorker (pg_notify)
        
        # 2. Rebuild Model (dari file asli Anda)
        PaginatedConversationListResponse.model_rebuild()
        logger.debug("PaginatedConversationListResponse model rebuilt.")

        # 3. Jalankan Scheduler & Background Jobs
        setup_scheduler_jobs() #
        scheduler.start()
        logger.info("APScheduler (background jobs) berhasil dimulai.")
        
    except Exception as e:
        logger.critical(f"FATAL: Gagal saat startup: {e}", exc_info=True)
        # Hentikan aplikasi jika startup gagal
        raise e

    yield # Aplikasi berjalan

    # --- SHUTDOWN ---
    logger.info("Aplikasi FastAPI memulai shutdown...")
    
    # 1. Hentikan semua worker & scheduler
    if scheduler.running:
        scheduler.shutdown(wait=False) # Matikan scheduler
        logger.info("APScheduler dimatikan.")
        
    stop_embedding_worker()
    stop_rebalance_worker()
    stop_cleanup_worker()
    logger.info("Semua worker dihentikan.")

    # 2. Tutup Koneksi Eksternal
    await disconnect_redis_pubsub()
    await close_asyncpg_pool()
    logger.info("Semua koneksi (Redis Pub/Sub, AsyncPG) ditutup.")
    logger.info("Aplikasi FastAPI shutdown selesai.")


app = FastAPI(
    title="AI Collaborative Canvas API",
    version="0.4.3",
    description="Backend for a collaborative canvas with an intelligent AI agent.",
    lifespan=lifespan # [REFACTOR] Gunakan lifespan yang baru
)

# Setup OpenTelemetry BEFORE middleware
setup_opentelemetry(app) # [REKOMENDASI] Kirim 'app'

# Add metrics middleware
app.middleware("http")(metrics_middleware) #

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Untuk dev: izinkan semua origin (ganti di produksi)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)  #

app.include_router(api_router, prefix="/api/v1")  #
