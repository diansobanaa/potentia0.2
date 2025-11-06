from pydantic import BaseModel, Field
from typing import Optional, List # <-- Pastikan List diimpor
from uuid import UUID
from enum import Enum

class WorkspaceType(str, Enum): personal = "personal"; team = "team"
class MemberRole(str, Enum): admin = "admin"; member = "member"; guest = "guest"

class WorkspaceCreate(BaseModel):
    name: str
    type: WorkspaceType = WorkspaceType.personal

class WorkspaceUpdate(BaseModel):
    """Skema payload untuk PATCH /workspaces/{workspace_id}"""
    name: str = Field(..., min_length=1, max_length=100)

class Workspace(BaseModel):
    id: UUID = Field(alias='workspace_id')
    owner_user_id: UUID
    name: str
    type: WorkspaceType
    workspace_metadata: Optional[dict] = None
    
    class Config:
        from_attributes = True
        populate_by_name = True # <-- Pastikan ini ada

class WorkspaceMember(BaseModel):
    id: UUID
    workspace_id: UUID
    user_id: UUID
    role: MemberRole
    class Config:
        from_attributes = True

# --- TAMBAHKAN CLASS BARU DI BAWAH INI ---

class PaginatedWorkspaceListResponse(BaseModel):
    """
    Model respons untuk daftar workspace yang dipaginasi.
    Digunakan oleh GET /workspaces/
    """
    items: List[Workspace]
    total: int
    page: int
    size: int
    total_pages: int