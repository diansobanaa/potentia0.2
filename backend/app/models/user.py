#backend\app\models\user.py
from pydantic import BaseModel, EmailStr, Field 
from typing import Optional, List 
from uuid import UUID
from enum import Enum

class SubscriptionTier(str, Enum):
    user = "user"
    pro = "pro"
    admin = "admin"

class User(BaseModel):
    id: UUID = Field(alias='user_id')
    email: EmailStr
    name: Optional[str] = None
    subscription_tier: SubscriptionTier
    
    class Config:
        from_attributes = True
        populate_by_name = True


class UserMetadataUpdate(BaseModel):
    """
    Skema untuk data di dalam 'user_metadata' (JSONB).
    Fokus pada 'no hp' (phone_number).
    """
    phone_number: Optional[str] = Field(None, description="Nomor telepon pengguna.")

class UserUpdate(BaseModel):
    """
    Skema payload untuk endpoint [PATCH /auth/me].
    Semua field bersifat opsional untuk 'PATCH'.
    """
    name: Optional[str] = Field(None, description="Nama lengkap baru pengguna.", min_length=1)
    email: Optional[EmailStr] = Field(None, description="Alamat email baru pengguna.")
    metadata: Optional[UserMetadataUpdate] = Field(None, description="Metadata baru pengguna.")