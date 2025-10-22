from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from enum import Enum

class MessageRole(str, Enum): user = "user"; ai = "ai"

class MessageCreate(BaseModel):
    content: str

class Message(BaseModel):
    id: UUID
    conversation_id: UUID
    role: MessageRole
    content: str
    timestamp: datetime
    class Config:
        from_attributes = True

class Conversation(BaseModel):
    id: UUID
    user_id: Optional[UUID]
    canvas_id: Optional[UUID]
    start_time: datetime
    end_time: Optional[datetime]
    metadata: Optional[dict]
    class Config:
        from_attributes = True