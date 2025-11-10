# File: backend/app/models/canvas.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from enum import Enum

class CanvasRole(str, Enum):
    owner = "owner"
    admin = "admin"
    editor = "editor"
    viewer = "viewer"

class CanvasCreate(BaseModel):
    """
    Model Pydantic untuk data yang DIHARAPKAN saat membuat canvas baru.
    """
    title: str = Field(..., description="Judul canvas")
    icon: Optional[str] = Field(None, description="Ikon canvas")
    workspace_id: Optional[UUID] = Field(None, description="ID workspace jika canvas milik workspace")
    canvas_metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata tambahan untuk canvas")

class CanvasUpdate(BaseModel):
    """
    Model Pydantic untuk data yang OPSIONAL saat memperbarui canvas.
    """
    title: Optional[str] = Field(None, description="Judul canvas")
    icon: Optional[str] = Field(None, description="Ikon canvas")
    is_archived: Optional[bool] = Field(None, description="Status arsip canvas")
    canvas_metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata tambahan untuk canvas")

class Canvas(BaseModel):
    """
    Model Pydantic utama untuk data Canvas.
    """
    id: UUID = Field(alias='canvas_id')
    workspace_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    creator_user_id: UUID
    title: str
    icon: Optional[str] = None
    is_archived: bool = False
    canvas_metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    summary_text: Optional[str] = None
    
    class Config:
        """Konfigurasi internal untuk model Pydantic."""
        from_attributes = True
        populate_by_name = True

class CanvasResponse(Canvas):
    """
    Model Pydantic untuk response canvas.
    """
    pass

class CanvasListResponse(BaseModel):
    """
    Model Pydantic untuk response daftar canvas.
    """
    id: UUID = Field(alias='canvas_id')
    title: str
    icon: Optional[str] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        """Konfigurasi internal untuk model Pydantic."""
        from_attributes = True
        populate_by_name = True

class CanvasMember(BaseModel):
    """
    Model Pydantic untuk anggota canvas.
    """
    id: UUID
    canvas_id: UUID
    user_id: UUID
    role: CanvasRole
    granted_at: datetime
    
    class Config:
        """Konfigurasi internal untuk model Pydantic."""
        from_attributes = True
        populate_by_name = True

class CanvasPermission(BaseModel):
    """
    Model Pydantic untuk permission canvas.
    """
    can_write: bool = Field(..., description="Apakah user dapat menulis ke canvas")
    role: str = Field(..., description="Role user di canvas")
    is_owner: bool = Field(..., description="Apakah user adalah owner canvas")
    is_creator: bool = Field(..., description="Apakah user adalah creator canvas")

class CanvasMemberInvite(BaseModel):
    """
    Model Pydantic untuk undangan anggota canvas.
    """
    invite_id: UUID
    canvas_id: UUID
    inviter_user_id: UUID
    invitee_email: str
    role: CanvasRole
    status: str  # e.g., 'pending', 'accepted', 'rejected'
    created_at: datetime
    
    class Config:
        from_attributes = True
        populate_by_name = True