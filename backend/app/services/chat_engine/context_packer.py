# File: backend/app/services/chat_engine/context_packer.py

import logging
import asyncio
import tiktoken
from uuid import UUID
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from supabase import Client as SupabaseClient

# Impor "Jalur Baca" (Read Path)
from app.db.queries.conversation.user_preference_reader import (
    get_user_facts_and_rules,
    get_user_semantic_memories
)

if TYPE_CHECKING:
    from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

# --- 2. Definisikan Anggaran & Tokenizer ---
MAX_CONTEXT_TOKEN_BUDGET = 6144 # 6K token
try:
    TOKENIZER = tiktoken.get_encoding("cl100k_base")
except Exception:
    logger.warning("Gagal memuat tiktoken, beralih ke estimasi split()")
    TOKENIZER = None

class ContextPacker:
    """
    Bertanggung jawab untuk "Jalur Baca" (Read Path) hibrida.
    Mengambil Fakta/Aturan (SQL) dan Memori (Vektor),
    lalu "mengepaknya" (pack) ke dalam satu string konteks
    yang aman (tidak melebihi batas token).
    """
    
    def __init__(
        self, 
        client: SupabaseClient, 
        embedding_service: 'EmbeddingService'
    ):
        self.client = client
        self.embedding_service = embedding_service
        self.tokenizer = TOKENIZER
        logger.debug("ContextPacker (V8) diinisialisasi.")

    def _count_tokens(self, text: str) -> int:
        """Helper untuk menghitung token dengan aman."""
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            return len(text.split()) 
    
    async def build_context(
        self,
        user_id: UUID,
        system_prompt: str,       # (Biaya Tetap #1)
        requeried_prompt: str,      # (Biaya Tetap #2)
        original_user_query: str,   # (Untuk pencarian Vektor)
        history_messages: List[Dict[str, Any]], 
        current_summary: str
    ) -> str:
        """
        (V8) Mengambil data hibrida (SQL+Vektor) DAN mengepak SEMUA konteks
        (Personalisasi + Riwayat) agar pas dalam ANGGARAN DINAMIS.
        """
        logger.info(f"Membangun konteks hibrida (V8 - Full Budgeting) untuk user {user_id}...")
        
        # --- TAHAP 1: Hitung Anggaran Dinamis (Dynamic Budget) ---
        
        fixed_token_cost = 0
        fixed_token_cost += self._count_tokens(system_prompt) 
        fixed_token_cost += self._count_tokens(requeried_prompt)
        fixed_token_cost += 50 # Buffer
        
        dynamic_token_budget = MAX_CONTEXT_TOKEN_BUDGET - fixed_token_cost
        
        if dynamic_token_budget <= 0:
            logger.warning(f"Anggaran token habis HANYA oleh prompt sistem/kueri. Tidak ada ruang untuk konteks.")
            return "(Tidak ada anggaran token tersisa untuk konteks)"

        logger.info(f"Anggaran Konteks Dinamis V8: {dynamic_token_budget} token.")
        total_tokens_used = 0
        final_context_blocks = []

        # --- TAHAP 2: Ambil Data (SQL & Vektor secara paralel) ---
        
        facts_rules_data = []
        semantic_memory_data = []
        try:
            vector_search_query = f"{original_user_query} {requeried_prompt}"
            logger.info(f"[Jalur Baca V8] Kueri Vektor: {vector_search_query[:150]}...")
            
            prompt_embedding = await self.embedding_service.generate_embedding(
                text=vector_search_query or "", task_type="retrieval_query"
            )
            
            (facts_rules_data, semantic_memory_data) = await asyncio.gather(
                get_user_facts_and_rules(self.client, user_id),
                get_user_semantic_memories(self.client, user_id, prompt_embedding)
            )
            logger.info(f"[Jalur Baca V8] Mengambil {len(facts_rules_data)} Fakta/Aturan dan {len(semantic_memory_data)} Memori.")

        except Exception as e:
            logger.error(f"[Jalur Baca V8] Gagal mengambil data hibrida: {e}")
        
        # --- TAHAP 3: Pengepakan Konteks Dinamis (Sesuai Prioritas) ---

        # PRIORITAS 1: FAKTA & ATURAN (SQL)
        facts_block = ["--- FAKTA & ATURAN PENGGUNA (WAJIB DIPATUHI) ---"]
        facts_count = 0
        if facts_rules_data:
            for fakta in facts_rules_data:
                teks = f"- ({fakta.get('type', 'FAKTA')}): {fakta.get('description', '')}"
                token_count = self._count_tokens(teks)
                
                if total_tokens_used + token_count <= dynamic_token_budget:
                    facts_block.append(teks)
                    total_tokens_used += token_count
                    facts_count += 1
                else:
                    break 
        if facts_count == 0:
            facts_block.append("(Tidak ada fakta atau aturan yang tersimpan)")
        final_context_blocks.append("\n".join(facts_block))

        # PRIORITAS 2: MEMORI SEMANTIK (Vektor)
        memori_block = ["--- MEMORI SEMANTIK RELEVAN (UNTUK REFERENSI) ---"]
        memori_count = 0
        if semantic_memory_data:
            for memori in semantic_memory_data:
                teks = f"- ({memori.get('type', 'MEMORI')}): {memori.get('content', '')}"
                token_count = self._count_tokens(teks)
                
                if total_tokens_used + token_count <= dynamic_token_budget:
                    memori_block.append(teks)
                    total_tokens_used += token_count
                    memori_count += 1
                else:
                    break
        if memori_count == 0:
            memori_block.append("(Tidak ada memori semantik yang relevan dengan kueri ini)")
        final_context_blocks.append("\n".join(memori_block))

        # PRIORITAS 3: RINGKASAN SAAT INI
        if current_summary and current_summary.strip() and current_summary != "Tidak ada.":
            teks = f"### RINGKASAN PERCAKAPAN\n{current_summary.strip()}"
            token_count = self._count_tokens(teks)
            if total_tokens_used + token_count <= dynamic_token_budget:
                final_context_blocks.append(teks)
                total_tokens_used += token_count

        # PRIORITAS 4: RIWAYAT PESAN TERKINI
        history_block = ["### RIWAYAT PERCAKAPAN TERKINI"]
        history_count = 0
        if history_messages:
            for msg in reversed(history_messages): 
                role = "Pengguna" if msg.get('role') == 'user' else "Asisten"
                teks = f"{role}: {msg.get('content', '').strip()}"
                token_count = self._count_tokens(teks)
                
                if total_tokens_used + token_count <= dynamic_token_budget:
                    history_block.insert(1, teks) 
                    total_tokens_used += token_count
                    history_count += 1
                else:
                    break
        if history_count == 0:
            history_block.append("(Tidak ada riwayat pesan yang relevan atau muat)")
        final_context_blocks.append("\n".join(history_block))
        
        # Gabungkan semuanya
        logger.info(
            f"Pengepakan Konteks V8 Selesai: "
            f"Total Token Konteks Dinamis: {total_tokens_used}/{dynamic_token_budget}. "
            f"(Anggaran Penuh: {MAX_CONTEXT_TOKEN_BUDGET} | Biaya Tetap: {fixed_token_cost})"
        )
        return "\n\n".join(final_context_blocks)