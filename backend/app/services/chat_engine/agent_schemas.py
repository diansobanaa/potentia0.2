# File: backend/app/services/chat_engine/agent_schemas.py
# (Diperbarui v3.2 - Menambahkan RerankedDocuments & PruningResult)

from pydantic import BaseModel, Field
from typing import Optional, Literal, List, Dict, Any
# Impor skema Pydantic yang sudah ada dari API
from app.services.chat_engine.schemas import ExtractedPreference

class IntentClassification(BaseModel):
    """
    Skema output terstruktur untuk node 'classify_intent'.
    """
    intent: Literal["simple_chat", "agentic_request", "rag_query"] = Field(
        ...,
        description="Klasifikasi niat utama pengguna."
    )
    potential_preference: bool = Field(
        default=False,
        description="Set True jika pesan pengguna kemungkinan mengandung fakta, aturan, atau preferensi baru."
    )
    
class RagQueryTransform(BaseModel):
    """
    Skema output terstruktur untuk node 'query_transform'.
    (NFR Poin 9: Hybrid Search)
    """
    rag_query: str = Field(
        ..., 
        description="Kueri pencarian semantik (vektor) yang dioptimalkan."
    )
    ts_query: str = Field(
        ..., 
        description="Kueri pencarian keyword (teks) yang dioptimalkan untuk tsquery (misal: 'kata1 & kata2')."
    )

class ToolApprovalRequest(BaseModel):
    """
    Skema output terstruktur untuk node 'reflection_node' (HiTL).
    """
    tool_name: str = Field(..., description="Nama tool yang memerlukan persetujuan.")
    tool_args: Dict[str, Any] = Field(..., description="Argumen yang akan digunakan.")
    reason: str = Field(..., description="Alasan mengapa AI ingin menjalankan tool ini.")

# [PERBAIKAN v3.2] Menambahkan skema yang hilang (Kekurangan #1)
class RerankedDocument(BaseModel):
    """Satu dokumen yang telah di-rerank oleh LLM."""
    original_index: int = Field(
        ..., 
        description="Indeks asli (0, 1, 2, ...) dari dokumen dalam daftar input."
    )
    relevance_score: float = Field(
        ..., 
        description="Skor relevansi baru (0.0-1.0) yang diberikan oleh LLM.",
        ge=0.0, le=1.0
    )
    reasoning: str = Field(
        ..., 
        description="Penjelasan singkat mengapa dokumen ini relevan atau tidak."
    )

class RerankedDocuments(BaseModel):
    """
    Skema output terstruktur untuk node 'rerank_context'.
    (NFR Poin 9)
    """
    reranked_results: List[RerankedDocument] = Field(
        ..., 
        description="Daftar 5 dokumen teratas yang telah di-rerank."
    )
# === AKHIR PERBAIKAN ===

class PrioritizedMessage(BaseModel):
    """Skema untuk 'chatgpt flow' pruning node."""
    index: int = Field(..., description="Indeks asli dari pesan.")
    priority: Literal["P1", "P2", "P3"] = Field(..., description="Prioritas yang ditetapkan oleh LLM.")

class PruningResult(BaseModel):
    """Skema output untuk 'manage_context_window' node."""
    prioritized_messages: List[PrioritizedMessage]