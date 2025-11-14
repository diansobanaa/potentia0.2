# backend/app/test_judge.py

import asyncio
import logging
from uuid import UUID
from typing import Dict, Any, List, Optional
from unittest.mock import MagicMock

# --- IMPOR DARI PACKAGE UTAMA ---
from app.services.chat_service import ChatService
from app.services.chat_engine.schemas import ChatRequest
from app.models.user import User, SubscriptionTier 
from app.core.config import settings
from app.db.queries.conversation import conversation_queries, context_queries, message_queries, log_queries
from app.services.chat_engine.judge_chain import get_judge_chain 

# Konfigurasi logging 
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] TEST_SCRIPT: %(message)s')
logger = logging.getLogger("TEST_SCRIPT")


# --- INICIALISASI GLOBAL ---
JUDGE_CHAIN_INSTANCE = None 
TEST_USER_ID = UUID("53f576a7-fbc1-46f4-8d42-996c94f06ab2") 
TEST_USER = User(id=TEST_USER_ID, email="test@potentia.com", subscription_tier=SubscriptionTier.admin)
mock_auth_info = {"user": TEST_USER, "client": MagicMock()} 
# NOTE: Tambahkan Mock untuk argumen ke-4 (Misal: Tools List atau Main Agent)
MOCK_MAIN_AGENT = MagicMock() 


# --- FUNGSI MOCK LAINNYA (TIDAK BERUBAH) ---

def initialize_settings():
    """
    Memastikan settings memiliki nilai untuk LLM sebelum JudgeChain diinisialisasi.
    """
    global JUDGE_CHAIN_INSTANCE
    settings.GEMINI_API_KEY = settings.GEMINI_API_KEY or "DUMMY_API_KEY_FOR_TESTING"
    settings.GEMINI_RERANKER_MODEL = settings.GEMINI_RERANKER_MODEL or "gemini-2.5-flash"
    settings.DEFAULT_MODEL = settings.DEFAULT_MODEL or "gemini-2.5-pro"

    if JUDGE_CHAIN_INSTANCE is None:
        JUDGE_CHAIN_INSTANCE = get_judge_chain()

class MockEmbeddingService:
    async def generate_embedding(self, text: str, task_type: str = "retrieval_query") -> List[float]:
        await asyncio.sleep(0.01) 
        logger.info(f"MOCK EMBEDDING: '{text[:25]}...'")
        return [0.5] * 1536 

# --- MOCK QUERY FUNCTIONS (Dihilangkan untuk fokus pada perbaikan) ---

conversation_queries.get_or_create_conversation = lambda client, user_id, conversation_id: \
    {"conversation_id": conversation_id or UUID("10000000-0000-0000-0000-000000000001")}

context_queries.get_active_context_by_user = lambda client, user_id: None 

def mock_find_relevant_summaries(client, user_id, query_embedding, match_threshold: float = 0.7, match_count: int = 5):
    logger.info("MOCK DB: RAG dijalankan, mengembalikan 1 summary kandidat.")
    return [{
        "summary_id": UUID("30000000-0000-0000-0000-000000000003"),
        "context_id": UUID("30000000-0000-0000-0000-000000000003"),
        "summary_text": "Pengguna pernah membahas proyek marketing besar di Q3 2024.",
        "similarity": 0.85
    }]
context_queries.find_relevant_summaries = mock_find_relevant_summaries

message_queries.add_message = lambda *args, **kwargs: {"message_id": UUID("99999999-9999-9999-9999-000000000001"), "content": "mocked"}
log_queries.create_decision_log = lambda *args, **kwargs: {}


# --- FUNGSI UTAMA UNTUK TES ---

async def run_chat_test(message: str, conversation_id: Optional[UUID] = None):
    
    initialize_settings() 

    logger.info(f"\n=======================================================")
    logger.info(f"TES DIMULAI: Pesan: '{message[:50]}...'")
    logger.info(f"=======================================================")

    # Inisialisasi ChatService (DI)
    # --- PERBAIKAN DI SINI: MENAMBAH ARGUMEN KE-4 ---
    chat_service = ChatService(
        mock_auth_info, 
        MockEmbeddingService(), 
        JUDGE_CHAIN_INSTANCE, 
        MOCK_TOOLS_LIST # <-- ARGUMEN KE-4 YANG SEBENARNYA DIBUTUHKAN
    )
    
    try:
        response = await chat_service.handle_chat_turn(
            ChatRequest(message=message, conversation_id=conversation_id)
        )
        logger.info(f"TES SUKSES. Keputusan AI: {response.ai_response}")
        return response
    except Exception as e:
        logger.error(f"TES GAGAL DENGAN EXCEPTION: {type(e).__name__}: {e}")
        return None

async def main():
    # --- TES 1: ALUR 'NEW' ---
    response1 = await run_chat_test(
        message="Saya ingin membahas topik baru, yaitu perubahan iklim.",
        conversation_id=None 
    )

    if response1:
        new_convo_id = response1.conversation_id
        new_context_id = response1.context_id
        
        # --- TES 2: ALUR 'CONTINUE' ---
        def mock_get_active_context_exists(client, user_id):
            return {
                "context_id": new_context_id,
                "conversation_id": new_convo_id,
                "summary": [{"summary_text": "Pengguna baru saja memulai diskusi tentang perubahan iklim."}],
                "status": "active"
            }
        context_queries.get_active_context_by_user = mock_get_active_context_exists

        logger.info("\nTEST 2: Melanjutkan Topik (Judge harus memutuskan 'Continue')")
        await run_chat_test(
            message="Apa kebijakan utama yang harus kita ambil di COP29?",
            conversation_id=new_convo_id
        )
        
        # --- TES 3: ALUR 'SWITCH' ---
        def mock_get_active_context_irrelevant(client, user_id):
            return {
                "context_id": new_context_id,
                "conversation_id": new_convo_id,
                "summary": [{"summary_text": "Topik saat ini adalah memasak dan resep makanan."}],
                "status": "active"
            }
        context_queries.get_active_context_by_user = mock_get_active_context_irrelevant
        
        logger.info("\nTEST 3: Mengganti Topik (Judge harus memutuskan 'Switch')")
        await run_chat_test(
            message="Bagaimana cara saya melihat hasil proyek marketing saya di Q3?",
            conversation_id=new_convo_id 
        )


# Jalankan skrip
if __name__ == "__main__":
    asyncio.run(main())