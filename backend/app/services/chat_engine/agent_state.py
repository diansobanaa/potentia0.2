# File: backend/app/services/chat_engine/agent_state.py
# (Diperbarui v2.6 - Menghapus dependensi 'auth_info')

from typing import TypedDict, Optional, List, Dict, Any
from datetime import datetime
from langchain_core.messages import BaseMessage

# Impor model Pydantic yang sudah ada untuk preferensi
from app.services.chat_engine.schemas import ExtractedPreference

class AgentState(TypedDict, total=False):
    """
    Mendefinisikan struktur data utama (JSON-serializable) yang mengalir 
    melalui LangGraph dan disimpan di Redis Checkpointer.
    
    (v2.6: Menghapus dependensi non-serializable 'auth_info' - Perbaikan Gap #3)
    """
    
    # === 1. Metadata Traceability & Keamanan (Wajib ada di awal) ===
    request_id: str
    trace_id: Optional[str]
    user_id: str
    permissions: List[str] # (Di-load saat inisialisasi)
    conversation_id: str
    created_at: datetime

    # [HAPUS] Dependensi tidak boleh disimpan di state
    # auth_info: Optional[Dict[str, Any]] 
    
    # === 2. Data Inti Percakapan ===
    user_message: str
    chat_history: List[BaseMessage]

    # === 3. Hasil Node Klasifikasi & RAG ===
    intent: str
    potential_preference: bool
    rag_query: Optional[str]
    ts_query: Optional[str] # [BARU] Untuk Hybrid Search
    retrieved_docs: List[Dict[str, Any]]
    provenance: List[Dict[str, Any]]
    reranked_docs: List[Dict[str, Any]]
    compressed_context: str

    # === 4. Hasil Eksekusi & Status ===
    # [BARU] Menyimpan tool calls yang diusulkan sebelum refleksi
    pending_tool_calls: Optional[List[Dict[str, Any]]] 
    
    # [BARU] Menyimpan permintaan HiTL jika dijeda
    tool_approval_request: Optional[Dict[str, Any]]
    
    tool_history: List[dict]
    final_response: str
    extracted_preferences: Optional[ExtractedPreference]

    # === 5. Metadata Operasional & Error ===
    errors: List[dict]
    retry_count: int

    # Token & cost tracking
    input_token_count: int
    output_token_count: int
    cost_estimate: float
    api_call_count: int  # Make sure this exists