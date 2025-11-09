# File: backend/app/models/workspace.py

from pydantic import (
    BaseModel, Field, EmailStr, ConfigDict, model_validator
)
from typing import Optional, List, Dict, Any
from uuid import UUID
from enum import Enum

# =======================================================================
# Definisi ENUM untuk konsistensi data
# =======================================================================

class WorkspaceType(str, Enum):
    """Mendefinisikan tipe workspace (personal vs tim)."""
    personal = "personal"
    team = "team"

class MemberRole(str, Enum):
    """Mendefinisikan role anggota yang valid di 'WorkspaceMembers'."""
    admin = "admin"
    member = "member"
    guest = "guest"

class InvitationType(str, Enum):
    """
    Mendefinisikan tipe undangan di 'WorkspaceInvitations'.
    Ini diperlukan untuk memperbaiki 'violates not-null constraint'.
    
    Note: Format enum harus sesuai dengan yang didefinisikan di database.
    Biasanya menggunakan lowercase atau format yang sesuai dengan konvensi.
    """
    USER_ID = "invite"
    EMAIL = "EMAIL"

class InvitationAction(str, Enum):
    """Mendefinisikan tindakan yang valid untuk merespons undangan."""
    ACCEPT = "accept"
    REJECT = "reject"




# =======================================================================
# Model untuk Workspace (Resource 4)
# =======================================================================

class WorkspaceCreate(BaseModel):
    """Skema Pydantic untuk validasi payload saat MEMBUAT workspace."""
    name: str
    type: WorkspaceType = WorkspaceType.personal

class WorkspaceUpdate(BaseModel):
    """Skema Pydantic untuk validasi payload saat MEMPERBARUI workspace."""
    name: str = Field(..., min_length=1, max_length=100)

class Workspace(BaseModel):
    """Skema Pydantic untuk MEREPRESENTASIKAN data workspace dari database."""
    id: UUID = Field(alias='workspace_id')
    owner_user_id: UUID
    name: str
    type: WorkspaceType
    workspace_metadata: Optional[dict] = None
    
    class Config:
        from_attributes = True
        populate_by_name = True

class WorkspaceMember(BaseModel):
    """Skema Pydantic untuk merepresentasikan data dari tabel 'WorkspaceMembers'."""
    id: UUID
    workspace_id: UUID
    user_id: UUID
    role: MemberRole
    class Config:
        from_attributes = True

class PaginatedWorkspaceListResponse(BaseModel):
    """Skema Pydantic untuk MENGEMBALIKAN daftar workspace yang dipaginasi."""
    items: List[Workspace]
    total: int
    page: int
    size: int
    total_pages: int

# =======================================================================
# Model untuk Workspace Members (Resource 3)
# =======================================================================

# --- [PERUBAHAN LOGIKA] ---
# Model ini sekarang mendukung logika 'Invite-Only' Anda
class WorkspaceMemberInviteOrAdd(BaseModel):
    """
    Skema payload untuk POST /workspaces/{id}/members.
    
    Fitur:
    Model ini fleksibel, memungkinkan frontend mengirim:
    1. 'user_id' (untuk mengundang pengguna yang sudah ada).
    2. 'email' (untuk mengundang pengguna eksternal).
    
    Validator di bawah memastikan hanya salah satu yang disediakan.
    """
    email: Optional[EmailStr] = Field(None, description="Email pengguna yang akan diundang (jika pengguna eksternal).")
    user_id: Optional[UUID] = Field(None, description="User ID pengguna yang akan ditambahkan (jika pengguna sudah ada).")
    
    role: MemberRole = Field(default=MemberRole.member, description="Role yang akan diberikan.")

    @model_validator(mode="before")
    def check_email_or_user_id(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fallback Validasi:
        Memastikan payload berisi 'email' ATAU 'user_id', tetapi tidak keduanya.
        """
        has_email = values.get("email")
        has_user_id = values.get("user_id")
        
        if not has_email and not has_user_id:
            raise ValueError("Harus menyediakan 'email' atau 'user_id'.")
        if has_email and has_user_id:
             raise ValueError("Hanya boleh menyediakan 'email' atau 'user_id', tidak keduanya.")
        return values
    
    model_config = ConfigDict(extra="forbid") # Fallback: Menolak field tambahan
# --- [AKHIR PERUBAHAN MODEL] ---

class WorkspaceMemberUpdate(BaseModel):
    """
    Skema payload untuk PATCH /workspaces/{id}/members/{user_id}.
    Hanya mengizinkan perubahan 'role'.
    """
    role: MemberRole = Field(..., description="Role baru untuk anggota workspace.")
    
    model_config = ConfigDict(extra="forbid") # Fallback: Menolak field tambahan

class WorkspaceMemberDetails(BaseModel):
    """
    Skema Pydantic untuk data pengguna (sub-set dari User model).
    Digunakan dalam 'WorkspaceMemberResponse' untuk keamanan.
    """
    user_id: UUID
    name: Optional[str] = None
    email: EmailStr

class WorkspaceMemberResponse(BaseModel):
    """
    Skema respons untuk GET /workspaces/{id}/members.
    Menggabungkan 'role' anggota dengan detail 'user'.
    """
    role: MemberRole
    user: WorkspaceMemberDetails
    
    class Config:
        from_attributes = True


class WorkspaceInvitationRespond(BaseModel):
    """
    Skema payload untuk POST /invitations/workspace/respond.
    Digunakan oleh pengguna yang login untuk menerima/menolak undangan.
    """
    token: str = Field(..., description="Token undangan unik yang diterima (misal: dari email).")
    action: InvitationAction = Field(..., description="Tindakan yang diambil (accept atau reject).")
    
    model_config = ConfigDict(extra="forbid")