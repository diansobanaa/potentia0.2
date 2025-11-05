import logging
from typing import Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_core.output_parsers import PydanticOutputParser 
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from langchain_core.output_parsers import StrOutputParser
# --- PERBAIKAN: Tambahkan RunnableLambda ke impor ini ---
from langchain_core.runnables import Runnable, RunnableLambda
# ----------------------------------------------------
from datetime import datetime # <-- TAMBAHKAN IMPOR INI
# --------------------
# --- IMPOR DARI FILE ANDA ---
from app.core.config import settings
# HAPUS JudgeMeta dari impor di bawah ini:
from app.services.chat_engine.schemas import JudgeDecision 
from app.prompts import ai_judge_prompt_templates as judge_prompts

logger = logging.getLogger(__name__)

# --- Variabel Global untuk Singleton ---
JUDGE_CHAIN_INSTANCE: Optional[Runnable] = None 

# --- PENGATURAN KEAMANAN (NONAKTIFKAN SEMUA) ---
SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
} if HarmCategory and HarmBlockThreshold else None


def get_fallback_chain() -> Runnable:
    """ 
    Chain cadangan yang dijamin selalu berhasil (Hanya jika inisialisasi LLM gagal).
    """
    logger.warning("Menggunakan FALLBACK CHAIN (Mocked JSON) untuk Judge.")
    fallback_data = {
        "is_ambiguous": False,
        "clarification_question": None,
        "decision": "New",
        "requeried_prompt": "Fallback: LLM Gagal Inisialisasi.",
        "chosen_summary_id": None,
        "reason": "FALLBACK MANUAL: LLM API GAGAL INISIALISASI.",
        "meta": {
            "judge_version": "v1.0.0 (FALLBACK)",
            "context_confidence": 0.01,
            "retrieved_summary_candidates": 0,
            "chosen_summary_title": None,
            "timestamp": datetime.now().isoformat()
        }
    }
    # Mengembalikan Runnable yang selalu mengembalikan JSON string ini
    return RunnableLambda(lambda x: JudgeDecision(**fallback_data))


def get_judge_chain() -> Runnable:
    """
    Menginisialisasi dan mengembalikan Rantai LCEL untuk AI Judge (Singleton).
    """
    global JUDGE_CHAIN_INSTANCE
    
    if JUDGE_CHAIN_INSTANCE is None:
        logger.info("Menginisialisasi Judge Chain Singleton...")
        
        try:
            llm = ChatGoogleGenerativeAI(
                model=settings.GEMINI_RERANKER_MODEL, 
                google_api_key=settings.GEMINI_API_KEY,
                temperature=0.0,
                # --- PERBAIKAN: Tambahkan safety_settings di sini ---
                safety_settings=SAFETY_SETTINGS
            )
            
            prompt = ChatPromptTemplate.from_template(judge_prompts.JUDGE_SYSTEM_INSTRUCTION)
            
            # Bind model ke skema output Pydantic
            # JUDGE_CHAIN_INSTANCE = prompt | llm.with_structured_output(JudgeDecision)
            
            # --- PERBAIKAN: Hapus with_structured_output dan GUNAKAN StrOutputParser ---
            JUDGE_CHAIN_INSTANCE = prompt | llm | StrOutputParser()
            # ---------

            logger.info("Judge Chain Singleton berhasil dibuat (Safety Filters Dinonaktifkan).")

        except Exception as e:
            logger.critical(f"FATAL: Gagal inisialisasi Gemini Client: {e}. Menggunakan FALLBACK CHAIN.")
            JUDGE_CHAIN_INSTANCE = get_fallback_chain()
            
    return JUDGE_CHAIN_INSTANCE