# File: backend/app/core/config.py
# (Diperbarui Fase 5 - Menambahkan TAVILY_API_KEY & LANGGRAPH_ROLLOUT_PERCENT)

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from uuid import UUID

class Settings(BaseSettings):
    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    
    DATABASE_URL: str 

    JWT_SECRET: str
    SUPABASE_JWT_SECRET: str

    # Google Gemini
    GEMINI_API_KEY: str
    GEMINI_GENERATIVE_MODEL: str 
    GEMINI_RERANKER_MODEL: str
    GEMINI_ASESOR_MODEL: str
    
    # [BARU] Kunci API untuk Tools Eksternal (Fase 2)
    TAVILY_API_KEY: Optional[str] = Field(None, description="Kunci API untuk Tavily Search tool.")
    
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

    # Observability
    OTEL_EXPORTER_OTLP_ENDPOINT: Optional[str] = None

    # [BARU] Feature Flag untuk LangGraph (Fase 2)
    LANGGRAPH_ROLLOUT_PERCENT: float = Field(
        default=1.0, 
        description="Persentase (0.0 hingga 1.0) trafik chat yang akan menggunakan LangGraph v2.1."
    )

    # Debug mode
    DEBUG: bool = False
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8')

    
settings = Settings()