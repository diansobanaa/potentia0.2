# File: backend/app/services/chat_engine/schemas.py

from __future__ import annotations 
from typing import Optional, Literal, Dict, Any, List
# --- PERBAIKAN: Impor 'uuid4' juga ---
from uuid import UUID, uuid4
from datetime import datetime
from pydantic import BaseModel, Field, model_validator, ConfigDict

# ============================================================
# 🧩 MODEL: JUDGE DECISION
# ============================================================

class JudgeDecision(BaseModel):
    """
    Representasi hasil keputusan dari LLM "Context Judge"
    """
    is_ambiguous: bool = Field(..., description="Apakah input pengguna ambigu?")
    clarification_question: Optional[str] = Field(None, description="Pertanyaan klarifikasi jika ambiguous.")
    reason: str = Field(..., description="Penjelasan reason dari keputusan.")
    requeried_prompt: Optional[str] = Field(
        None, 
        description="Prompt hasil rewrite yang lebih jelas dan mandiri. Bisa None jika is_ambiguous=True."
    )
    context_assessment: Optional[
        Literal["New", "Continue", "Switch"]
    ] = Field(None, description="Keputusan konteks (lanjut, ganti, atau buat baru).")
    
    # --- PERBAIKAN: Ganti 'uuid.UUID' menjadi 'UUID' ---
    chosen_summary_id: Optional[UUID] = Field(
        None, description="ID summary terpilih jika context_assessment=Switch."
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @model_validator(mode="before")
    def normalize_values(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Membersihkan nilai kosong atau placeholder dari LLM."""
        optional_keys_to_clean = [
            "clarification_question", 
            "context_assessment", 
            "chosen_summary_id"
        ]
        empty_values = ["", "N/A", "null", None] 

        for key in optional_keys_to_clean:
            if key in values and values[key] in empty_values:
                values[key] = None

        if not values.get("context_assessment"):
            values["context_assessment"] = "New"

        return values

    class Config:
        from_attributes = True


# --- FUNGSI HELPER (YANG HILANG) ---
def normalize_llm_garbage(values: Dict[str, Any], keys_to_clean: List[str]) -> Dict[str, Any]:
    """
    Fungsi terpusat untuk membersihkan placeholder 'malas' dari LLM.
    """
    empty_values = ["", "N/A", "null", "None", "Tidak ada", "Tidak relevan"]
    
    for key in keys_to_clean:
        if key in values:
            value = values[key]
            if isinstance(value, str) and value.strip() in empty_values:
                values[key] = None
            elif isinstance(value, str) and not value.strip():
                 values[key] = None
    return values

# --- AKHIR FUNGSI HELPER ---


class PreferenceItem(BaseModel):
    """Mewakili satu preferensi pengguna yang diekstrak."""
    
    # --- PERBAIKAN: Tambahkan 'preference_id' (dari file sebelumnya) & gunakan 'uuid4' ---
    preference_id: str = Field(
        default_factory=lambda: str(uuid4()), # <-- Gunakan 'uuid4'
        description="UUIDv4 unik untuk preferensi ini"
    )
    type: Literal[
        "GAYA_BAHASA", "FORMAT", "TOPIK", "LARANGAN", "METODE",
        "PROFIL_PENGGUNA", "MEMORI", "TUJUAN_PENGGUNA", "KENDALA_TUGAS"
    ] = Field(..., description="Kategori preferensi")
    description: str = Field(..., description="Penjelasan jelas tentang preferensi")
    trigger_text: str = Field(..., description="Teks pengguna yang memicu deteksi ini")
    confidence_score: float = Field(..., description="Skor keyakinan (0.0 hingga 1.0)")

    @model_validator(mode="before")
    def normalize_fields(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Membersihkan field string yang mungkin 'malas' diisi oleh LLM."""
        keys_to_clean = ["description", "trigger_text"]
        return normalize_llm_garbage(values, keys_to_clean)

class ExtractedPreference(BaseModel):
    """Objek yang berisi list preferensi."""
    preferences: List[PreferenceItem] = Field(
        default_factory=list,
        description="List dari semua objek preferensi yang terdeteksi"
    )
    
    @model_validator(mode="before")
    def clean_preferences_list(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if "preferences" in values and values["preferences"] is None:
            values["preferences"] = []
        return values


class AIResponseStructured(BaseModel):
    """
    Skema JSON output akhir yang WAJIB dipatuhi oleh LLM.
    """
    thinking: str = Field(
        ..., 
        description="Rencana kognitif (CoT) langkah-demi-langkah AI, mengikuti Elemen 1, 2, dan 3 dari prompt."
    )
    ai_response: str = Field(
        ..., 
        description="Jawaban akhir yang akan dilihat oleh pengguna, dalam format teks biasa (natural)."
    )
    extracted_preference: ExtractedPreference = Field(
        default_factory=ExtractedPreference,
        description="Objek yang berisi daftar preferensi pengguna yang diekstrak."
    )

    @model_validator(mode="before")
    def normalize_fields(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Membersihkan field string yang mungkin 'malas' diisi oleh LLM."""
        keys_to_clean = ["thinking", "ai_response"]
        return normalize_llm_garbage(values, keys_to_clean)


# ============================================================
# 🧩 MODEL: CHAT REQUEST (Asumsi dari file Anda sebelumnya)
# ============================================================

class ChatRequest(BaseModel):
    """
    Payload utama dari pengguna ke endpoint /chat
    """
    message: str = Field(..., description="Pesan teks dari pengguna.")
    
    # --- PERBAIKAN: Ganti 'uuid.UUID' menjadi 'UUID' ---
    conversation_id: Optional[UUID] = Field(None, description="ID percakapan aktif.")
    context_id: Optional[UUID] = Field(None, description="ID konteks aktif (jika ada).")

    class Config:
        from_attributes = True

# ============================================================
# 🧩 MODEL: CHAT RESPONSE (Asumsi dari file Anda sebelumnya)
# ============================================================

class ChatResponse(BaseModel): 
    """
    Respons API utama yang dikembalikan ke frontend
    """
    ai_response: str = Field(..., description="Jawaban akhir dari AI Agent.")
    
    # --- PERBAIKAN: Ganti 'uuid.UUID' menjadi 'UUID' ---
    conversation_id: UUID = Field(..., description="ID percakapan.")
    context_id: Optional[UUID] = Field(
        None,
        description="ID konteks yang aktif."
    )
    user_id: Optional[UUID] = Field(None, description="ID pengguna.")
    session_id: Optional[str] = Field(None, description="ID sesi interaksi.")
    user_message: Optional[str] = Field(None, description="Input asli pengguna.")
    final_response: Optional[str] = Field(None, description="Teks jawaban final (bisa sama dengan ai_response).")
    judge_decision: Optional[Dict[str, Any]] = Field(
        None, description="Hasil mentah dari Context Judge."
    )
    thinking: Optional[str] = Field(None, description="Log pemikiran (CoT) dari AI.")
    extracted_user_preferences: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list, 
        description="List preferensi yang diekstrak."
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True
        
    @model_validator(mode="after")
    def fill_user_message(self) -> ChatResponse:
        if not self.user_message:
            self.user_message = "(tidak ada input)"
        return self

# ============================================================
# 🧩 MODEL: UNTUK ENDPOINT DAFTAR PESAN
# ============================================================

class MessageListItem(BaseModel):
    """Representasi ringkas dari satu pesan (user atau assistant)."""
    message_id: UUID
    role: Literal["user", "assistant", "system", "tool"]
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PaginatedMessageListResponse(BaseModel):
    """Response model untuk endpoint list pesan dalam satu conversation."""
    items: List[MessageListItem]
    total: int
    page: int
    size: int
    total_pages: int


# ============================================================
# 🧩 MODEL: UNTUK ENDPOINT LIST CONVERSATIONS
# ============================================================

class ConversationListItem(BaseModel):
    """Representasi ringkas dari sebuah conversation untuk list."""
    conversation_id: UUID
    title: str
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PaginatedConversationListResponse(BaseModel):
    """Response model untuk endpoint list conversation dengan pagination."""
    items: List[ConversationListItem]
    total: int
    page: int
    size: int
    total_pages: int


try:
    PaginatedConversationListResponse.model_rebuild()
except Exception as e:
    # Log jika terjadi error saat rebuild, tapi jangan crash aplikasi
    print(f"Warning: Failed to rebuild PaginatedConversationListResponse model: {e}")