from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
import sys 
from app.api.v1.api import api_router
from app.core.config import settings
import logging.config
from app.services.chat_engine.schemas import PaginatedConversationListResponse

# --- KONFIGURASI LOGGING (Ganti basicConfig) ---
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False, # JANGAN nonaktifkan logger bawaan
    "formatters": {
        "default": {
            # Format bisa disesuaikan
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
        # Root logger (default untuk semua logger yang tidak diatur secara eksplisit)
        # Atur ke INFO untuk log umum aplikasi, atau DEBUG jika masih debugging RAG
        "": {
            "handlers": ["console"],
            "level": "INFO", # <-- NAIKKAN ke INFO (atau tetap DEBUG jika perlu)
            "propagate": False, # Jangan teruskan ke root logger Python bawaan
        },
        # Logger aplikasi Anda (misalnya, semua di bawah 'app')
        # Jika Anda ingin log DEBUG hanya dari kode Anda:
        "app": {
            "handlers": ["console"],
            "level": "DEBUG", # <-- Biarkan DEBUG untuk kode aplikasi Anda
            "propagate": False, # Jangan teruskan lagi
        },
        # --- NAIKKAN LEVEL UNTUK LIBRARY BERISIK ---
        "httpx": { # Library HTTP yang mungkin dipakai supabase-py
            "handlers": ["console"],
            "level": "INFO", # Naikkan levelnya
            "propagate": False,
        },
        "httpcore": { # Dependency httpx
             "handlers": ["console"],
             "level": "INFO",
             "propagate": False,
         },
        "hpack": { # Library HTTP/2
            "handlers": ["console"],
            "level": "INFO", # Naikkan levelnya
            "propagate": False,
        },
         "google.api_core": { # Library Google API
             "handlers": ["console"],
             "level": "INFO",
             "propagate": False,
         },
         "google.auth": { # Library Google Auth
             "handlers": ["console"],
             "level": "INFO",
             "propagate": False,
         },
        # --- Logger Uvicorn (opsional, bisa diatur levelnya) ---
         "uvicorn": {
             "handlers": ["console"],
             "level": "INFO",
             "propagate": False,
         },
         "uvicorn.error": {
             "level": "INFO", # Biarkan default
              "propagate": False,
         },
         "uvicorn.access": {
             "handlers": ["console"],
             "level": "INFO", # Biarkan default
             "propagate": False,
         },
    },
}

logging.config.dictConfig(LOGGING_CONFIG)
# --- AKHIR KONFIGURASI LOGGING ----

app = FastAPI(
    title="AI Collaborative Canvas API",
    version="0.1.0",
    description="Backend for a collaborative canvas with an intelligent AI agent."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

# Buat lifespan manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Kode ini akan dijalankan saat aplikasi startup
    print("Application startup...")
    try:
        # Panggil model_rebuild() untuk model yang bermasalah
        PaginatedConversationListResponse.model_rebuild()
        print("PaginatedConversationListResponse model rebuilt successfully.")
    except Exception as e:
        print(f"Warning: Failed to rebuild PaginatedConversationListResponse model: {e}")

    yield  # Aplikasi berjalan di sini

    # Kode ini akan dijalankan saat aplikasi shutdown (opsional)
    print("Application shutdown.")

# Inisialisasi FastAPI dengan lifespan manager
app = FastAPI(
    title="My App API",
    lifespan=lifespan, # <-- Gunakan lifespan
    # ... konfigurasi lainnya
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to the AI Collaborative Canvas API."}