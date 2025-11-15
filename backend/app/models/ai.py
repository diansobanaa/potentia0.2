# File: backend/app/models/ai.py
# Domain models for Chat AI (Conversation, Message, Context)

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any, Literal
from uuid import UUID
from datetime import datetime


# ============================================================
# CONVERSATION MODELS
# ============================================================

class ConversationBase(BaseModel):
    """Base model for conversation."""
    title: str = Field(..., min_length=1, max_length=200, description="Conversation title")


class ConversationCreate(ConversationBase):
    """Model for creating a new conversation."""
    conversation_id: Optional[UUID] = Field(None, description="Optional UUID (generated if None)")


class ConversationUpdate(BaseModel):
    """Model for updating conversation."""
    title: str = Field(..., min_length=1, max_length=200, description="New conversation title")


class ConversationDetail(ConversationBase):
    """Detailed conversation model with all fields."""
    conversation_id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ConversationListItem(BaseModel):
    """Conversation item for list views."""
    conversation_id: UUID
    title: str
    updated_at: datetime
    message_count: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# MESSAGE MODELS
# ============================================================

class MessageBase(BaseModel):
    """Base model for message."""
    role: Literal["user", "assistant", "system", "tool"] = Field(..., description="Message role")
    content: str = Field(..., description="Message content")


class MessageCreate(MessageBase):
    """Model for creating a new message."""
    conversation_id: UUID
    context_id: Optional[UUID] = None
    model_used: Optional[str] = Field(None, description="LLM model identifier")
    input_tokens: int = Field(0, ge=0, description="Input token count")
    output_tokens: int = Field(0, ge=0, description="Output token count")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(None, description="Tool call data")


class MessageDetail(MessageBase):
    """Detailed message model with all fields."""
    message_id: UUID
    user_id: UUID
    conversation_id: UUID
    context_id: Optional[UUID]
    model_used: Optional[str]
    input_tokens: int
    output_tokens: int
    tool_calls: Optional[List[Dict[str, Any]]]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class MessageListItem(BaseModel):
    """Message item for list views."""
    message_id: UUID
    role: Literal["user", "assistant", "system", "tool"]
    content: str
    created_at: datetime
    model_used: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# CONTEXT MODELS
# ============================================================

class ContextBase(BaseModel):
    """Base model for context."""
    context_type: str = Field(default="main", description="Type of context")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Context metadata")


class ContextCreate(ContextBase):
    """Model for creating a new context."""
    conversation_id: UUID


class ContextUpdate(BaseModel):
    """Model for updating context."""
    metadata: Dict[str, Any] = Field(..., description="Updated metadata")
    is_active: Optional[bool] = Field(None, description="Active status")


class ContextDetail(ContextBase):
    """Detailed context model with all fields."""
    context_id: UUID
    user_id: UUID
    conversation_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# PAGINATION MODELS
# ============================================================

class PaginatedConversations(BaseModel):
    """Paginated conversation list response."""
    items: List[ConversationListItem]
    total: int
    page: int
    size: int
    total_pages: int


class PaginatedMessages(BaseModel):
    """Paginated message list response."""
    items: List[MessageListItem]
    total: int
    page: int
    size: int
    total_pages: int


# ============================================================
# STATISTICS MODELS
# ============================================================

class TokenUsageStats(BaseModel):
    """Token usage statistics for a conversation."""
    conversation_id: UUID
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    message_count: int


class ConversationStats(BaseModel):
    """Comprehensive conversation statistics."""
    conversation_id: UUID
    title: str
    message_count: int
    token_usage: TokenUsageStats
    created_at: datetime
    updated_at: datetime
