# File: backend/app/core/config.py
# (DIPERBAIKI - Menambahkan DATABASE_URL yang hilang)

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from uuid import UUID

class Settings(BaseSettings):
    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    
    # [PERBAIKAN] Tambahkan field ini agar Pydantic mau menerimanya
    DATABASE_URL: str 

    JWT_SECRET: str
    SUPABASE_JWT_SECRET: str

    # Google Gemini
    GEMINI_API_KEY: str
    # Model Utama (Besar) untuk Generasi Jawaban & Tool Calling
    GEMINI_GENERATIVE_MODEL: str 
    #Model Ringan & Cepat untuk Reranking
    GEMINI_RERANKER_MODEL: str
    GEMINI_ASESOR_MODEL: str
    
    # Model Deepseek untuk Pembaruan judul Conversation
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_API_URL: str = "https://api.deepseek.com/chat/completions"

    # RAG Service
    DEFAULT_ROLE_ID: UUID
    SEEDING_ADMIN_KEY: str  

    AI_AGENT_USER_ID: UUID # ID Pengguna untuk AI Agent
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # Email
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""

    OTEL_EXPORTER_OTLP_ENDPOINT: Optional[str] = None

    # Debug mode
    DEBUG: bool = False
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8')

    
settings = Settings() 