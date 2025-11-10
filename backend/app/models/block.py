# File: backend/app/models/block.py
# (DISESUAIKAN dengan skema SQL baru)

from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, Literal
from uuid import UUID
from datetime import datetime
from enum import Enum

class BlockType(str, Enum):
    text = "text"
    task_item = "task_item"
    heading_1 = "heading_1"
    heading_2 = "heading_2"
    image = "image"
    code = "code"

class BlockCreate(BaseModel):
    """
    Model Pydantic untuk data yang DIHARAPKAN saat membuat block baru.
    """
    parent_id: Optional[UUID] = None
    type: BlockType
    content: str
    properties: Optional[dict] = None
    y_order: Optional[str] = "a0"

class BlockUpdate(BaseModel):
    """
    Model Pydantic untuk data yang OPSIONAL saat memperbarui block.
    """
    content: Optional[str] = None
    properties: Optional[dict] = None
    y_order: Optional[str] = None

class BlockOperationPayload(BaseModel):
    """
    Payload yang dikirim dari klien untuk memicu operasi mutasi
    pada block (POST /mutate atau WebSocket H1).
    """
    client_op_id: str = Field(
        ..., 
        description="UUID unik yang dihasilkan klien untuk idempotency (Tugas 2)."
    )
    block_id: Optional[UUID] = Field(
        None, 
        description="ID block yang dimutasi. Opsional jika action='create'."
    )
    canvas_id: UUID = Field(
        ..., 
        description="ID canvas target."
    )
    update_data: Dict[str, Any] = Field(
        ...,
        description="Data update block (misal: {'content': 'teks baru', 'y_order': 'b1'})."
    )
    action: Literal["create", "update", "delete"] = Field(
        ...,
        description="Jenis operasi."
    )
    expected_version: Optional[int] = Field(
        None, 
        description="Nomor versi block yang diharapkan klien sebelum update/delete (Optimistic Locking)."
    )

class Block(BaseModel):
    """
    Model Pydantic utama untuk data Block (Refleksi Skema DB v0.4.3).
    """
    
    id: UUID = Field(alias='block_id') 
    canvas_id: UUID
    parent_id: Optional[UUID]
    
    y_order: str
    version: int = Field(default=1)
    created_at: Optional[datetime] = None
    created_by: Optional[UUID] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[UUID] = None
    
    type: str # Diubah dari BlockType karena di DB disimpan sebagai TEXT
    content: str
    properties: Optional[dict] = None
    ai_metadata: Optional[dict] = None
    vector: Optional[Any] = None # VECTOR(760)
    
    class Config:
        """Konfigurasi internal untuk model Pydantic."""
        from_attributes = True
        populate_by_name = True