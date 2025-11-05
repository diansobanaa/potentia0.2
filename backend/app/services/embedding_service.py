# PARSE: 18-embedding-service-v2.py
import logging
import asyncio
import google.generativeai as genai
from typing import List
from app.core.config import settings
from app.services.interfaces import IEmbeddingService
from app.core.exceptions import EmbeddingGenerationError

# Konfigurasi logger
logger = logging.getLogger(__name__)

# Konfigurasi klien Google sekali saat modul di-load
try:
    if settings.GEMINI_API_KEY:
        genai.configure(api_key=settings.GEMINI_API_KEY)
    else:
        logger.warning("GEMINI_API_KEY tidak diatur. EmbeddingService tidak akan berfungsi.")
except Exception as e:
    logger.critical(f"Gagal mengkonfigurasi Google Gemini: {e}", exc_info=True)

def _embed_content_sync(text: str, task_type: str) -> List[float]:
    """
    Fungsi wrapper SINKRON (blocking) untuk genai.embed_content.
    Ini adalah logika asli dari file Anda.
    """
    try:
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type=task_type
        )
        return result["embedding"]
    except Exception as e:
        logger.error(f"Error internal saat memanggil genai.embed_content: {e}", exc_info=True)
        # Melemparkan exception untuk ditangkap oleh pemanggil async
        raise EmbeddingGenerationError(str(e))

class GeminiEmbeddingService(IEmbeddingService):
    """
    Implementasi konkret IEmbeddingService yang membungkus
    panggilan sinkron Google API di thread terpisah.
    """
    
    def __init__(self, model_name: str = "models/text-embedding-004"):
        self.model_name = model_name
        if not settings.GEMINI_API_KEY:
            logger.critical("GeminiEmbeddingService dibuat tanpa GEMINI_API_KEY.")

    async def generate_embedding(
        self, 
        text: str, 
        task_type: str = "retrieval_query"
    ) -> List[float]:
        """
        Secara ASINKRON menghasilkan embedding.
        
        Ini memanggil fungsi _embed_content_sync yang blocking
        di thread pool terpisah menggunakan asyncio.to_thread,
        sehingga event loop FastAPI tidak terblokir.
        """
        if not settings.GEMINI_API_KEY:
            raise EmbeddingGenerationError("GEMINI_API_KEY tidak diatur.")
        
        try:
            # Menjalankan fungsi SINKRON di thread terpisah
            embedding = await asyncio.to_thread(
                _embed_content_sync, 
                text, 
                task_type
            )
            return embedding
        except Exception as e:
            logger.error(f"Gagal menjalankan embedding_service.generate_embedding: {e}")
            # Pastikan exception yang dilempar adalah tipe yang kita harapkan
            if isinstance(e, EmbeddingGenerationError):
                raise
            raise EmbeddingGenerationError(str(e))