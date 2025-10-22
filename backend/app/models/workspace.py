from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from enum import Enum

class WorkspaceType(str, Enum): personal = "personal"; team = "team"
class MemberRole(str, Enum): admin = "admin"; member = "member"; guest = "guest"

class WorkspaceCreate(BaseModel):
    name: str
    type: WorkspaceType = WorkspaceType.personal

class Workspace(BaseModel):
    id: UUID
    owner_user_id: UUID
    name: str
    type: WorkspaceType
    workspace_metadata: Optional[dict] = None
    
    class Config:
        from_attributes = True

class WorkspaceMember(BaseModel):
    id: UUID
    workspace_id: UUID
    user_id: UUID
    role: MemberRole
    class Config:
        from_attributes = True