from pydantic import BaseModel, Field 
from typing import Optional, Any
from uuid import UUID
from enum import Enum

class BlockType(str, Enum):
    """
    Mendefinisikan tipe-tipe block yang valid dan dapat diterima oleh API.
    Menggunakan str Enum memastikan data yang masuk selalu konsisten.
    """
    text = "text"
    task_item = "task_item"
    heading_1 = "heading_1"
    heading_2 = "heading_2"
    image = "image"
    code = "code"

class BlockCreate(BaseModel):
    """
    Model Pydantic untuk data yang DIHARAPKAN saat membuat block baru.
    Ini digunakan sebagai validasi input untuk endpoint POST.
    """
    parent_id: Optional[UUID] = None
    type: BlockType
    content: str
    properties: Optional[dict] = None
    y_order: Optional[float] = 0.0

class BlockUpdate(BaseModel):
    """
    Model Pydantic untuk data yang OPSIONAL saat memperbarui block.
    Ini digunakan sebagai validasi input untuk endpoint PATCH.
    Semua field bersifat Opsional.
    """
    content: Optional[str] = None
    properties: Optional[dict] = None
    y_order: Optional[float] = None

class Block(BaseModel):
    """
    Model Pydantic utama untuk data Block.
    Ini merepresentasikan data yang ada di database DAN
    digunakan sebagai 'response_model' (validasi output) untuk API.
    """
    
    # --- TITIK PENTING (Perbaikan ResponseValidationError) ---
    # 'id' adalah nama field di model Pydantic kita (yang diharapkan oleh 'response_model').
    # 'block_id' adalah nama kolom di database Supabase Anda.
    # 'Field(alias=...)' memberitahu Pydantic untuk mengisi field 'id' ini
    # dengan nilai dari 'block_id' saat memuat data dari database.
    id: UUID = Field(alias='block_id') 
    # --------------------------------------------------------
    
    canvas_id: UUID
    parent_id: Optional[UUID]
    y_order: float
    type: BlockType
    content: str
    properties: Optional[dict] = None
    ai_metadata: Optional[dict] = None
    
    class Config:
        """Konfigurasi internal untuk model Pydantic."""
        
        # Mengizinkan Pydantic untuk memuat data dari atribut objek
        # (penting jika Anda mengembalikan objek ORM, bukan hanya dict).
        from_attributes = True
        
        # --- TITIK PENTING (Pasangan dari 'alias') ---
        # Ini mengizinkan Pydantic untuk mengisi field berdasarkan alias-nya ('block_id')
        # selain nama field-nya ('id'). WAJIB ADA agar alias berfungsi.
        populate_by_name = True

