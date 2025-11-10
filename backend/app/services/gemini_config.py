import google.generativeai as genai
from app.core.config import settings #
from typing import AsyncIterable
import logging

logger = logging.getLogger(__name__)

# Konfigurasi API key Gemini
try:
    genai.configure(api_key=settings.GEMINI_API_KEY)
except Exception as e:
    logger.critical(f"Gagal mengkonfigurasi Google Gemini: {e}", exc_info=True)

async def stream_gemini_response(prompt: str) -> AsyncIterable[str]:
    """
    Mengirimkan prompt ke Google Gemini API dan mengembalikan stream respons teks.
    Sumber:
    """
    try:
        # [PERBAIKAN] Menggunakan nama model dari settings,
        # bukan 'gemini-2.5-flash-preview-09-2025'
        model = genai.GenerativeModel(settings.GEMINI_GENERATIVE_MODEL) 
        
        stream = await model.generate_content_async(prompt, stream=True) 
        
        async for chunk in stream:
            if chunk.parts:
                yield chunk.text
            # (Logika penanganan 'else' sama seperti file asli)

    except Exception as e:
        logger.error(f"Error calling Gemini API stream: {e}", exc_info=True)
        yield f"Maaf, terjadi error saat menghubungi AI: {str(e)}"

async def call_gemini_api(prompt: str) -> str:
    """
    (Versi Lama - Non-Streaming)
    Mengirimkan prompt ke Google Gemini API dan mengembalikan respons teks lengkap.
    (Logika tidak berubah)
    Sumber:
    """
    full_response = ""
    try:
        async for chunk in stream_gemini_response(prompt):
             full_response += chunk
        if "Maaf, terjadi error" in full_response:
             return full_response
        if not full_response:
             logger.warning("Gemini stream completed but resulted in an empty response.")
             return "Maaf, AI tidak memberikan respons."
        return full_response
    except Exception as e:
        logger.error(f"Error collecting full response from Gemini stream: {e}", exc_info=True)
        return "Maaf, saya sedang mengalami kesulitan teknis untuk merespons."