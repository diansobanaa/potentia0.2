from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from enum import Enum

class SuperPromptType(str, Enum): Konstanta = "Konstanta"; super = "super"

class RoleCreate(BaseModel):
    super_master_prompt_type: SuperPromptType
    role_name: str
    description: str
    prompt_content: str
    keywords: Optional[List[str]] = None
    required_tier: str = 'user'

class Role(BaseModel):
    id: UUID
    super_master_prompt_type: Optional[SuperPromptType]
    role_name: str
    description: str
    prompt_content: str
    keywords: Optional[List[str]]
    is_active: bool
    version: int
    owner_user_id: Optional[UUID]
    required_tier: str
    class Config:
        from_attributes = True