# PARSE: 06-pydantic-models-v3.py
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID

# Menjelaskan "kontrak" data untuk endpoint RAG.
# File ini mendefinisikan struktur data JSON yang diharapkan
# untuk request (masukan) dan response (keluaran) dari
# endpoint /send.

class RagRequest(BaseModel):
    """
    Model Pydantic untuk data yang diterima dari frontend 
    di endpoint /send.
    
    Ini adalah payload (body) yang harus dikirim oleh klien
    saat meminta respons AI.
    """
    user_message: str = Field(
        ..., 
        description="Teks pesan yang diketik oleh pengguna."
    )
    
    conversation_id: Optional[UUID] = Field(
        default=None, 
        description=(
            "ID percakapan saat ini. Kirim 'null' atau jangan sertakan "
            "kunci ini jika ini adalah pesan pertama dalam percakapan baru. "
            "Backend akan membuat ID baru jika null."
        )
    )
    
    canvas_id: Optional[UUID] = Field(
        default=None, 
        description=(
            "ID canvas yang sedang aktif dilihat pengguna. "
            "Jika 'null' atau tidak disertakan, RAG untuk 'Blocks' (Langkah B10) "
            "akan dilewati. Ini untuk chat yang tidak terkait canvas."
        )
    )
    
    language_code: str = Field(
        default="id", 
        description=(
            "Kode bahasa (cth: 'id', 'en') untuk seleksi "
            "SystemPrompt dan MasterPrompt yang sesuai."
        )
    )

    class Config:
        """
        Konfigurasi Pydantic.
        json_schema_extra digunakan oleh FastAPI untuk menghasilkan
        contoh payload di dokumentasi /docs.
        """
        json_schema_extra = {
            "example": {
                "user_message": "Bantu saya kembangkan ide ini dari blok terakhir.",
                "conversation_id": "a1b2c3d4-e5f6-7890-a1b2-c3d4e5f67890",
                "canvas_id": "f0e1d2c3-b4a5-6789-f0e1-d2c3b4a56789",
                "language_code": "id"
            }
        }

class RagResponse(BaseModel):
    """
    Model Pydantic untuk respons standar yang dikirim kembali 
    ke frontend dari endpoint /send.
    
    Ini adalah payload (body) yang akan diterima klien
    setelah pemrosesan AI berhasil.
    """
    ai_response: str = Field(
        ..., 
        description="Teks respons lengkap yang dihasilkan oleh AI (Gemini)."
    )
    
    conversation_id: UUID = Field(
        ..., 
        description=(
            "ID percakapan yang diproses. Jika request mengirim 'null', "
            "ini akan menjadi UUID baru yang dibuat oleh server. "
            "Klien harus menyimpan ini untuk pesan berikutnya."
        )
    )
    
    ai_message_id: UUID = Field(
        ..., 
        description=(
            "ID unik dari pesan respons AI yang baru saja disimpan di "
            "database (tabel 'Messages')."
        )
    )
    
    class Config:
        """
        Konfigurasi Pydantic.
        json_schema_extra digunakan oleh FastAPI untuk menghasilkan
        contoh respons di dokumentasi /docs.
        """
        json_schema_extra = {
            "example": {
                "ai_response": "Tentu, ide Anda tentang 'strategi pemasaran digital' bisa dikembangkan...",
                "conversation_id": "a1b2c3d4-e5f6-7890-a1b2-c3d4e5f67890",
                "ai_message_id": "z9y8x7w6-v5u4-t3s2-r1q0-p9o8n7m6l5k4"
            }
        }