import httpx
import json
import logging
from typing import AsyncGenerator

# [DIUBAH] Impor untuk Gemini
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# Impor dari kode Anda
from app.core.config import settings
from app.prompts.title_generator import SYSTEM_PROMPT_TITLE_GENERATOR

logger = logging.getLogger(__name__)

# [DIUBAH] Pengaturan keamanan Gemini (dari judge_chain.py Anda)
SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
} if HarmCategory and HarmBlockThreshold else None


class DeepSeekClient:
    """
    Client untuk streaming pembuatan judul.
    CATATAN: Logika internal SEMENTARA DIGANTI untuk menggunakan Gemini
    sesuai permintaan.
    """

    def __init__(self):
        # [DIUBAH] Inisialisasi Gemini
        if not settings.GEMINI_API_KEY:
            logging.error("GEMINI_API_KEY tidak ditemukan di config.")
            raise ValueError("GEMINI_API_KEY harus di-set.")
        
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            # Kita gunakan model Asesor yang ringan untuk tugas ini
            #
            self.model = genai.GenerativeModel(
                model_name=settings.GEMINI_ASESOR_MODEL,
                safety_settings=SAFETY_SETTINGS
            )
            logging.info(f"DeepSeekClient (dialihkan ke Gemini) menggunakan model: {settings.GEMINI_ASESOR_MODEL}")
        except Exception as e:
            logging.error(f"Gagal menginisialisasi model Gemini: {e}")
            raise

    async def stream_title_from_deepseek(
        self, user_message: str, ai_response: str
    ) -> AsyncGenerator[str, None]:
        """
        Async generator untuk streaming judul.
        [DIUBAH] Sekarang memanggil Gemini alih-alih DeepSeek.
        """
        
        full_conversation_context = f"PENGGUNA: {user_message}\n\nAI: {ai_response}"
        
        # [DIUBAH] Format prompt untuk Gemini
        prompt_content = [
            SYSTEM_PROMPT_TITLE_GENERATOR,
            "--- KONTEKS PERCAKAPAN ---",
            full_conversation_context,
            "--- JUDUL SINGKAT (MAKS 4 KATA) ---"
        ]
        
        generation_config = genai.GenerationConfig(
            max_output_tokens=30,
            temperature=0.5
        )

        try:
            # [DIUBAH] Memanggil Gemini .generate_content_async (streaming)
            stream = await self.model.generate_content_async(
                prompt_content,
                generation_config=generation_config,
                stream=True
            )

            async for chunk in stream:
                if chunk.parts:
                    yield chunk.text
                # Jika tidak ada chunk.parts, itu mungkin blok keamanan atau akhir
                elif chunk.candidates and chunk.candidates[0].finish_reason != 'STOP':
                     logger.warning(f"Stream judul Gemini berhenti prematur: {chunk.candidates[0].finish_reason}")
                     yield "[Error AI]"


        except Exception as e:
            logger.error(f"Error tidak terduga di stream Gemini (untuk judul): {e}")
            yield "[Error Internal]"

# Instance ini sekarang ditenagai Gemini, tapi namanya tetap sama
# sehingga `title_stream_service` tidak perlu diubah.
deepseek_client = DeepSeekClient()

