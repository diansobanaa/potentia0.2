# File: backend/app/services/chat_engine/reranker.py
# (File Baru - Rencana v2.1 Fase 3)

import logging
from typing import List, Dict, Any, Optional
from langchain_cohere import CohereRerank
from app.core.config import settings

logger = logging.getLogger(__name__)

class RerankerService:
    """
    Menyediakan layanan reranking terpusat.
    Mengimplementasikan NFR Poin 9 (Batching Reranker).
    """
    def __init__(self):
        self.reranker = None
        if settings.COHERE_API_KEY:
            try:
                self.reranker = CohereRerank(
                    api_key=settings.COHERE_API_KEY,
                    model="rerank-english-v3.0", # Ganti ke 'rerank-multilingual-v3.0' untuk non-Inggris
                    top_n=5 # Ambil top 5 dokumen terbaik
                )
                logger.info("Cohere Reranker (rerank-multilingual-v3.0) berhasil diinisialisasi.")
            except ImportError:
                logger.error("Package 'langchain-cohere' tidak terinstal. Reranker tidak akan berfungsi.")
            except Exception as e:
                logger.error(f"Gagal menginisialisasi CohereRerank: {e}")
        else:
            logger.warning("COHERE_API_KEY tidak diatur. Reranker akan dilewati (fallback).")

    async def arerank_documents(
        self, 
        query: str, 
        documents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Melakukan rerank dokumen secara batch.
        
        Args:
            query: Kueri pengguna (rag_query).
            documents: List[dict], setiap dict HARUS memiliki 'page_content'.

        Returns:
            List[dict] dokumen yang telah diurutkan ulang.
        """
        if not self.reranker:
            logger.warning("Reranker dilewati (tidak terkonfigurasi). Mengembalikan 5 dokumen teratas.")
            return documents[:5]
            
        if not documents:
            return []

        try:
            # Ubah format dokumen untuk Cohere
            docs_to_rerank = [{"text": doc.get("page_content", "")} for doc in documents]
            
            # Panggil .arerank (async)
            # NFR Poin 9: Ini adalah panggilan batch, bukan N panggilan individual.
            reranked_results = await self.reranker.arerank(
                query=query,
                documents=docs_to_rerank,
                rank_fields=["text"]
            )
            
            # Kembalikan dokumen asli, diurutkan berdasarkan hasil rerank
            reranked_docs = []
            for result in reranked_results:
                if result.relevance_score > 0.1: # Filter skor rendah
                    original_doc = documents[result.index]
                    original_doc["relevance_score"] = result.relevance_score
                    reranked_docs.append(original_doc)
            
            return reranked_docs

        except Exception as e:
            logger.error(f"Gagal melakukan rerank: {e}. Mengembalikan 5 dokumen teratas (fallback).")
            # NFR Poin 4 (Fallbacks)
            return documents[:5]

# --- Instance Singleton ---
reranker_service = RerankerService()