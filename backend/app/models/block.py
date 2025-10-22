from pydantic import BaseModel
from typing import Optional, Any
from uuid import UUID
from enum import Enum

class BlockType(str, Enum): text = "text"; task_item = "task_item"; heading_1 = "heading_1"; heading_2 = "heading_2"; image = "image"; code = "code"

class BlockCreate(BaseModel):
    parent_id: Optional[UUID] = None
    type: BlockType
    content: str
    properties: Optional[dict] = None
    y_order: Optional[float] = 0.0

class BlockUpdate(BaseModel):
    content: Optional[str] = None
    properties: Optional[dict] = None
    y_order: Optional[float] = None

class Block(BaseModel):
    id: UUID
    canvas_id: UUID
    parent_id: Optional[UUID]
    y_order: float
    type: BlockType
    content: str
    properties: Optional[dict] = None
    ai_metadata: Optional[dict] = None
    class Config:
        from_attributes = True