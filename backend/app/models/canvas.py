from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID

class CanvasCreate(BaseModel):
    title: str
    icon: Optional[str] = "📄"

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