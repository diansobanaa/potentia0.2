# File: backend/app/services/chat_engine/llm_chat_executor.py
# VERSI V6 (Teks-saja) - Untuk Arsitektur 3 Panggilan

import logging
import re  # <-- Impor Regex
import asyncio
from typing import Optional, Tuple

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
# --- Impor LangChain Parser Dihapus ---
# (PydanticOutputParser dan OutputParserException tidak lagi digunakan di file ini)

from app.prompts.developer_prompt import (
    MAIN_DEVELOPER_PROMPT,
    # (Template lain tidak diperlukan lagi)
    format_conversation_context
)
from app.core.config import settings
# --- PERUBAHAN: Kita tidak lagi mengimpor skema Pydantic untuk *parsing* ---
from app.services.chat_engine.schemas import AIResponseStructured, ExtractedPreference

logger = logging.getLogger(__name__)

class LLMExecutor:
    """
    LLMExecutor (V6 - Teks Saja):
    Hanya bertanggung jawab untuk Panggilan #2 (Spesialis).
    Tugasnya adalah menghasilkan <thinking> log dan ai_response (Teks).
    TUGAS EKSTRAKSI PREFERENSI TELAH DIHAPUS DARI KELAS INI.
    """

    def __init__(self):
        # Inisialisasi LLM utama (Model "Pintar/Mahal" Anda)
        self.llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_GENERATIVE_MODEL, # Misal: Gemini Pro
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.4,
            # PERINGATAN: Kita tidak bisa lagi memaksa output JSON di sini
            # response_mime_type="application/json" (HARUS DIHAPUS)
        )
        
        # --- PARSER, TEMPLATE, DAN CHAIN (V5) DIHAPUS ---
        logger.info("LLMExecutor (Mode Teks V6) diinisialisasi.")

    def _build_system_prompt(self, context_strategy: str, has_context: bool) -> str:
        """
        Bangun prompt sistem dasar (peran dan aturan utama).
        (Logika ini dipertahankan)
        """
        if has_context and context_strategy in ("Continue", "Switch"):
            system_prompt = (
                "[ROLE: Potentia | Context-Aware Assistant]\n"
                + MAIN_DEVELOPER_PROMPT.strip()
                + "\n\nAnda akan menjawab berdasarkan konteks yang diberikan."
            )
        else:
            # Untuk kasus 'New' atau tanpa konteks
            system_prompt = (
                "[ROLE: Potentia | Mode: Context-Aware Assistant]\n"
                "Anda adalah asisten produktivitas yang fokus pada kejelasan dan relevansi.\n"
                "Jika konteks tidak relevan, jawab dengan jujur dan bantu pengguna memulai percakapan baru.\n\n"
                + MAIN_DEVELOPER_PROMPT.strip()
            )
        
        # PENTING: Pastikan MAIN_DEVELOPER_PROMPT Anda sekarang berisi
        # instruksi format Teks/XML (<thinking>...</thinking>), BUKAN JSON.
        return system_prompt

    async def run_final_prompt(
        self,
        system_prompt: str, # <-- 1. TERIMA PROMPT SISTEM (BIAYA TETAP #1)
        formatted_context: str,
        requeried_query: Optional[str] = None,
        original_user_query: Optional[str] = None, 
        context_strategy: str = "New"
    ) -> str:
        """
        Jalankan prompt akhir (Panggilan #2) dan kembalikan output Teks MENTAH.
        """
        try:
            has_context = bool(formatted_context.strip())

            # --- Rakit Variabel Prompt ---
            system_prompt = self._build_system_prompt(context_strategy, has_context)
            
            final_requeried_query = (requeried_query or original_user_query or "").strip() or "(tidak ada input pengguna)"
            final_original_query = (original_user_query or "").strip() or "(tidak ada input pengguna)"
            final_context = formatted_context.strip() or "(tidak ada konteks tersedia)"

            # --- Debug Logging (Diperbarui) ---
            logger.critical("----------- system_prompt (BASE V6 - Teks) -----------")
            logger.critical(system_prompt)
            logger.critical("---------------------------------------------")
            logger.critical("----------- formatted_context (Hibrida) -----------------")
            logger.critical(final_context)
            logger.critical("---------------------------------------------")
            # (Original query tidak lagi relevan untuk V6 executor, tapi kita log)
            logger.critical("----------- original_user_query (Akan diabaikan oleh P#2) -----------------")
            logger.critical(final_original_query)
            logger.critical("---------------------------------------------")
            logger.critical("----------- requeried_query (Tugas Utama) -----------------")
            logger.critical(final_requeried_query)
            logger.critical("---------------------------------------------")

            # --- PERUBAHAN: Panggilan LLM Manual (Bukan Rantai) ---
            messages = [
                SystemMessage(content=system_prompt),
                # Konteks Hibrida (Fakta + Memori + Riwayat) disuntikkan di sini
                SystemMessage(content=f"KONTEKS YANG DIINJEKSI:\n{final_context}"),
                # Kueri yang sudah bersih dari Juri (P#1)
                HumanMessage(content=final_requeried_query)
            ]

            response = await self.llm.ainvoke(messages)
            raw_output = response.content.strip() if response and hasattr(response, "content") else ""
            
            if not raw_output:
                raise ValueError("Model (P#2 Spesialis) tidak mengembalikan output teks.")

            logger.info("✅ P#2 (Spesialis) berhasil mengembalikan Teks Mentah.")
            
            # Kembalikan TEKS MENTAH, BUKAN objek Pydantic
            return raw_output

        except Exception as e:
            # Menangkap semua error (misal, kegagalan koneksi LLM)
            logger.error(f"❌ Gagal mengeksekusi LLM Spesialis (P#2): {e}", exc_info=True)
            # Kembalikan string error agar bisa diparsing oleh chat_service
            return f"<thinking>[ERROR] Gagal Panggilan #2: {e}</thinking>Maaf, terjadi kesalahan internal saat memproses permintaan Anda."