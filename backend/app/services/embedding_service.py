# backend/app/services/embedding_service.py
# (Diperbarui untuk panggilan async native)

import logging
import asyncio
import google.generativeai as genai
from typing import List
from app.core.config import settings
from app.services.interfaces import IEmbeddingService
from app.core.exceptions import EmbeddingGenerationError

logger = logging.getLogger(__name__)

try:
    if settings.GEMINI_API_KEY:
        genai.configure(api_key=settings.GEMINI_API_KEY)
    else:
        logger.warning("GEMINI_API_KEY tidak diatur. EmbeddingService tidak akan berfungsi.")
except Exception as e:
    logger.critical(f"Gagal mengkonfigurasi Google Gemini: {e}", exc_info=True)


class GeminiEmbeddingService(IEmbeddingService):
    
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
        [PERBAIKAN] Secara ASINKRON menghasilkan embedding
        menggunakan panggilan 'embed_content_async' native.
        """
        if not settings.GEMINI_API_KEY:
            raise EmbeddingGenerationError("GEMINI_API_KEY tidak diatur.")
        
        try:
            # --- PERBAIKAN: Panggil 'embed_content_async' ---
            result = await genai.embed_content_async(
                model=self.model_name,
                content=text,
                task_type=task_type
            )
            return result["embedding"]
            # ----------------------------------------------

        except Exception as e:
            logger.error(f"Gagal menjalankan embedding_service.generate_embedding (async): {e}", exc_info=True)
            if isinstance(e, EmbeddingGenerationError):
                raise
            raise EmbeddingGenerationError(str(e))