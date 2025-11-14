"""
LLM Provider Factory - Frontend-driven model selection.
Backend auto-detects provider from model name.
"""
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# Model to provider mapping (static, can be moved to DB later)
MODEL_TO_PROVIDER = {
    # Gemini models
    "gemini-flash-lite-latest": "gemini",
    "gemini-2.5-pro": "gemini",
    "gemini-2.5-flash": "gemini",
    
    # OpenAI models
    "gpt-4o-mini": "openai",
    "gpt-5-pro": "openai",
    "gpt-4.1": "openai",
    
    # DeepSeek models
    "deepseek-chat": "deepseek",
    "deepseek-v3": "deepseek",
    "deepseek-r1": "deepseek",
    
    # Kimi models
    "moonshot-v1-32k": "kimi",
    "moonshot-v1-8k": "kimi",
    "moonshot-v1-128k": "kimi",
    "kimi-k2-thinking": "kimi",
    
    # XAI models
    "grok-4-fast-reasoning-latest": "xai",
    "grok-4": "xai",
    "grok-code-fast-1": "xai",
}

def get_provider_from_model(model: str) -> str:
    """Auto-detect provider from model name."""
    provider = MODEL_TO_PROVIDER.get(model)
    
    if not provider:
        # Fallback: guess from model prefix
        if model.startswith("gemini"):
            return "gemini"
        elif model.startswith("gpt"):
            return "openai"
        elif model.startswith("deepseek"):
            return "deepseek"
        elif model.startswith("moonshot") or model.startswith("kimi"):
            return "kimi"
        elif model.startswith("grok"):
            return "xai"
        else:
            raise ValueError(f"Unknown model: {model}. Supported models: {list(MODEL_TO_PROVIDER.keys())}")
    
    return provider


def get_chat_model(model: str, temperature: float = 0.2, **kwargs):
    """
    Build ChatModel from model identifier.
    Provider is auto-detected from model name.
    
    Args:
        model: Model identifier (e.g., 'gemini-2.5-flash', 'gpt-4o-mini')
        temperature: 0.0-2.0
        **kwargs: Additional provider-specific parameters
    
    Returns:
        LangChain ChatModel instance
    
    Raises:
        ValueError: If model is not supported
    """
    logger.info(
        f"🏭 get_chat_model called with: model={model}, "
        f"temperature={temperature}"
    )
    
    provider = get_provider_from_model(model)
    logger.info(f"🔍 Detected provider: {provider} for model: {model}")
    
    try:
        if provider == "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI
            logger.info(f"🤖 Creating Gemini client: {model} (temp={temperature})")
            client = ChatGoogleGenerativeAI(
                model=model,
                temperature=temperature,
                google_api_key=settings.GEMINI_API_KEY,
            )
            logger.info(f"✅ Created Gemini client for model: {model}")
            return client
        
        if provider == "openai":
            from langchain_openai import ChatOpenAI
            logger.info(f"🤖 Creating OpenAI client: {model} (temp={temperature})")
            client = ChatOpenAI(
                model=model,
                temperature=temperature,
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL,
            )
            logger.info(f"✅ Created OpenAI client for model: {model}")
            return client
        
        if provider == "deepseek":
            from langchain_openai import ChatOpenAI
            logger.info(f"🤖 Creating DeepSeek client: {model} (temp={temperature})")
            client = ChatOpenAI(
                model=model,
                temperature=temperature,
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.DEEPSEEK_BASE_URL,
            )
            logger.info(f"✅ Created DeepSeek client for model: {model}")
            return client
        
        if provider == "kimi":
            from langchain_openai import ChatOpenAI
            logger.info(f"🤖 Creating Kimi client: {model} (temp={temperature})")
            client = ChatOpenAI(
                model=model,
                temperature=temperature,
                api_key=settings.KIMI_API_KEY,
                base_url=settings.KIMI_BASE_URL,
            )
            logger.info(f"✅ Created Kimi client for model: {model}")
            return client
        
        if provider == "xai":
            from langchain_openai import ChatOpenAI
            logger.info(f"🤖 Creating XAI client: {model} (temp={temperature})")
            client = ChatOpenAI(
                model=model,
                temperature=temperature,
                api_key=settings.XAI_API_KEY,
                base_url=settings.XAI_BASE_URL,
            )
            logger.info(f"✅ Created XAI client for model: {model}")
            return client
    
    except Exception as e:
        logger.error(
            f"❌ Failed to init {provider}/{model}: {e}",
            exc_info=True
        )
        # Fallback to Gemini but track the error for user notification
        if provider != "gemini":
            logger.warning(
                f"⚠️  Fallback to Gemini DEFAULT_MODEL: "
                f"{settings.DEFAULT_MODEL}"
            )
            from langchain_google_genai import ChatGoogleGenerativeAI
            
            # Return Gemini client with error info attached
            gemini_client = ChatGoogleGenerativeAI(
                model=settings.DEFAULT_MODEL,
                temperature=temperature,
                google_api_key=settings.GEMINI_API_KEY,
            )
            # Attach error metadata for streaming service to detect
            gemini_client._fallback_error = {
                "original_model": model,
                "original_provider": provider,
                "error": str(e)
            }
            return gemini_client
        raise


def get_available_models() -> list[str]:
    """Get list of models backend can currently support based on available API keys."""
    available = []
    
    if settings.GEMINI_API_KEY:
        available.extend(["gemini-flash-lite-latest", "gemini-2.5-pro", "gemini-2.5-flash"])
    
    if settings.OPENAI_API_KEY:
        available.extend(["gpt-4o-mini", "gpt-5-pro", "gpt-4.1"])
    
    if settings.DEEPSEEK_API_KEY:
        available.extend(["deepseek-chat", "deepseek-v3", "deepseek-r1"])
    
    if settings.KIMI_API_KEY:
        available.extend(["moonshot-v1-32k", "moonshot-v1-8k", "moonshot-v1-128k", "kimi-k2-thinking"])
    
    if settings.XAI_API_KEY:
        available.extend(["grok-4-fast-reasoning-latest", "grok-4", "grok-code-fast-1"])
    
    return available
