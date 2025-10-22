from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
from enum import Enum

class SubscriptionTier(str, Enum):
    user = "user"
    pro = "pro"
    admin = "admin"

class User(BaseModel):
    id: UUID
    email: EmailStr
    name: Optional[str] = None
    subscription_tier: SubscriptionTier
    
    class Config:
        from_attributes = True