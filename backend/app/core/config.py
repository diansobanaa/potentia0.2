# File: backend/app/core/config.py
# (Disesuaikan untuk arsitektur 'model-dinamis' dari frontend)

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

    # External Tools
    TAVILY_API_KEY: Optional[str] = Field(None, description="Kunci API untuk Tavily Search tool.")

    # RAG Service
    DEFAULT_ROLE_ID: UUID
    SEEDING_ADMIN_KEY: str  
    AI_AGENT_USER_ID: UUID 
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # Email
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""

    # Observability
    OTEL_EXPORTER_OTLP_ENDPOINT: Optional[str] = None

    # Feature Flag
    LANGGRAPH_ROLLOUT_PERCENT: float = Field(default=1.0)

    # Debug mode
    DEBUG: bool = False
    
    # ===== LLM Provider Credentials =====
    # Backend internal models (RAG pipeline only)
    GEMINI_RERANKER_MODEL: str = Field(default="gemini-flash-lite-latest", env="GEMINI_RERANKER_MODEL")
    GEMINI_ASESOR_MODEL: str = Field(default="gemini-flash-lite-latest", env="GEMINI_ASESOR_MODEL")
    
    # Provider API keys & base URLs
    GEMINI_API_KEY: str = Field(default="", env="GEMINI_API_KEY")
    OPENAI_API_KEY: str = Field(default="", env="OPENAI_API_KEY")
    OPENAI_BASE_URL: str = Field(default="https://api.openai.com/v1", env="OPENAI_BASE_URL")
    DEEPSEEK_API_KEY: str = Field(default="", env="DEEPSEEK_API_KEY")
    DEEPSEEK_BASE_URL: str = Field(default="https://api.deepseek.com", env="DEEPSEEK_BASE_URL")
    KIMI_API_KEY: str = Field(default="", env="KIMI_API_KEY")
    KIMI_BASE_URL: str = Field(default="https://api.moonshot.cn/v1", env="KIMI_BASE_URL")
    XAI_API_KEY: str = Field(default="", env="XAI_API_KEY")
    XAI_BASE_URL: str = Field(default="https://api.x.ai/v1/chat/completions", env="XAI_BASE_URL")
    
    # Fallback defaults (only used if request has no llm_config)
    DEFAULT_MODEL: str = Field(
        default="gemini-2.5-flash",
        env="DEFAULT_MODEL"
    )
    DEFAULT_TEMPERATURE: float = Field(
        default=0.2,
        env="DEFAULT_TEMPERATURE"
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8'
    )


settings = Settings()

settings = Settings() 