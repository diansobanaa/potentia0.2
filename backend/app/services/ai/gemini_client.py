# File: (tempat kelas GeminiClient didefinisikan)

import google.generativeai as genai
from typing import Optional
from app.core.config import settings # Pastikan settings diimpor

class GeminiClient:
    """Wrapper untuk Gemini API dengan proper configuration."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        # --- PERBAIKAN: Ambil default dari settings ---
        model_name: Optional[str] = None, # Jadikan opsional
        # ---
        enable_automatic_function_calling: bool = False
    ):
        self.api_key = api_key or settings.GEMINI_API_KEY
        # --- PERBAIKAN: Gunakan settings jika model_name tidak diberikan ---
        self.model_name = model_name or settings.GEMINI_GENERATIVE_MODEL
        # ---
        self.enable_auto_function_calling = enable_automatic_function_calling

        # Configure once
        if not self.api_key:
             # Tambahkan error handling jika API key tidak ada
             raise ValueError("GEMINI_API_KEY tidak ditemukan di settings atau tidak diberikan.")
        genai.configure(api_key=self.api_key)

    def create_model(self, tools: list, system_instruction: Optional[str] = None): # Tambah system_instruction
        """Factory method untuk membuat GenerativeModel."""
        # Gunakan self.model_name yang sudah benar
        return genai.GenerativeModel(
            self.model_name,
            tools=tools,
            system_instruction=system_instruction # Teruskan instruksi
        )

    def start_chat(self, model, history: Optional[list] = None): # Tambah history
        """Start chat session dengan configuration."""
        # Gunakan self.enable_auto_function_calling
        return model.start_chat(
            enable_automatic_function_calling=self.enable_auto_function_calling,
            history=history or [] # Mulai dengan riwayat jika ada
        )