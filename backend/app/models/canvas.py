# File: backend/app/models/canvas.py

from pydantic import (
    BaseModel, Field, ConfigDict, EmailStr, model_validator 
)
from typing import Optional, List, Dict, Any
from uuid import UUID
from enum import Enum

class CanvasCreate(BaseModel):
    title: str
    icon: Optional[str] = "📄"

class CanvasMetaUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, description="Judul baru untuk canvas.")
    icon: Optional[str] = Field(None, description="Ikon emoji baru untuk canvas.")
    model_config = ConfigDict(extra="forbid")

class CanvasRole(str, Enum):
    """
    Mendefinisikan role yang valid di dalam tabel CanvasAccess.
    (Kita asumsikan 'editor' memiliki hak admin untuk canvas tersebut).
    """
    editor = "editor"
    viewer = "viewer"

class CanvasMemberInvite(BaseModel):
    """
    Model Pydantic untuk payload POST /canvases/{canvas_id}/members.
    Digunakan untuk mengundang pengguna baru ke canvas.
    """
    email: Optional[EmailStr] = Field(None, description="Email pengguna yang akan diundang.")
    user_id: Optional[UUID] = Field(None, description="User ID pengguna yang sudah ada untuk diundang.")
    
    role: CanvasRole = Field(..., description="Role yang akan diberikan (viewer/editor).")

    @model_validator(mode="before")
    def check_email_or_user_id(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Memastikan setidaknya salah satu 'email' atau 'user_id' ada."""
        if not values.get("email") and not values.get("user_id"):
            raise ValueError("Harus menyediakan 'email' atau 'user_id' untuk mengundang.")
        if values.get("email") and values.get("user_id"):
             raise ValueError("Hanya boleh menyediakan 'email' atau 'user_id', tidak keduanya.")
        return values
    
    model_config = ConfigDict(extra="forbid")

class Canvas(BaseModel):
    id: UUID = Field(alias='canvas_id')
    workspace_id: Optional[UUID]
    user_id: Optional[UUID]
    creator_user_id: UUID
    title: str
    icon: Optional[str]
    is_archived: bool = False
    
    class Config:
        from_attributes = True
        populate_by_name = True 

class PaginatedCanvasListResponse(BaseModel):
    items: List[Canvas]
    total: int
    page: int
    size: int
    total_pages: int