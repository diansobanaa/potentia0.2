# File: backend/app/models/schedule.py
# Versi 1.2 (Calendar-Centric)
# File ini mendefinisikan skema Pydantic untuk arsitektur penjadwalan baru.

from pydantic import (
    BaseModel, Field, EmailStr, ConfigDict, model_validator
)
from typing import Optional, List, Dict, Any, Literal
from uuid import UUID
from datetime import datetime
from enum import Enum

# =======================================================================
# LANGKAH 1: DEFINISI ENUM
# Mencerminkan ENUMs yang kita buat di database (SQL Langkah 2)
# =======================================================================

class CalendarVisibility(str, Enum):
    """
    Mengontrol visibilitas default Kalender.
    (Mencerminkan 'calendar_visibility_enum' di SQL).
    """
    private = "private"
    workspace = "workspace"
    public = "public"

class SubscriptionRole(str, Enum):
    """
    Mengontrol hak akses Pengguna ke Kalender.
    (Mencerminkan 'calendar_subscription_role_enum' di SQL).
    """
    owner = "owner"
    editor = "editor"
    viewer = "viewer"

class GuestRole(str, Enum):
    """
    Mengontrol hak akses Tamu di dalam satu Acara.
    (Mencerminkan 'guest_role_enum' di SQL).
    """
    guest = "guest"
    co_host = "co-host"

class RsvpStatus(str, Enum):
    """
    Status respons RSVP dari seorang Tamu.
    (Mencerminkan 'rsvp_status_enum' di SQL).
    """
    pending = "pending"
    accepted = "accepted"
    declined = "declined"


# =======================================================================
# LANGKAH 2: 5 MODEL TABEL INTI (UNTUK DATA DATABASE)
# Model-model ini digunakan sebagai 'response_model'
# =======================================================================

class Calendar(BaseModel):
    """
    Model Pydantic untuk Tabel: `Calendars`
    Mewakili "wadah" atau "folder" kalender.
    """
    id: UUID = Field(alias='calendar_id')
    name: str
    owner_user_id: Optional[UUID] = None
    workspace_id: Optional[UUID] = None
    visibility: CalendarVisibility
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
        populate_by_name = True # Mengizinkan alias 'calendar_id'

class CalendarSubscription(BaseModel):
    """
    Model Pydantic untuk Tabel: `CalendarSubscriptions`
    Mewakili langganan pengguna ke kalender.
    """
    id: UUID = Field(alias='subscription_id')
    user_id: UUID
    calendar_id: UUID
    role: SubscriptionRole
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True
        populate_by_name = True

class Schedule(BaseModel):
    """
    Model Pydantic untuk Tabel: `Schedules`
    Mewakili "sumber kebenaran" (source of truth) dari sebuah acara.
    """
    id: UUID = Field(alias='schedule_id')
    calendar_id: UUID
    title: str
    start_time: datetime # Disimpan sebagai UTC
    end_time: datetime   # Disimpan sebagai UTC
    schedule_metadata: Optional[Dict[str, Any]] = None # Untuk 'original_timezone'
    
    # Data RFC 5545 (Perulangan)
    rrule: Optional[str] = None
    rdate: Optional[List[str]] = None # Disimpan sebagai TEXT[] ISO string UTC
    exdate: Optional[List[str]] = None # Disimpan sebagai TEXT[] ISO UTC string
    
    parent_schedule_id: Optional[UUID] = None
    creator_user_id: UUID
    
    # Soft Delete & Versi
    is_deleted: bool
    deleted_at: Optional[datetime] = None
    version: int
    
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        populate_by_name = True

class ScheduleGuest(BaseModel):
    """
    Model Pydantic untuk Tabel: `ScheduleGuests`
    Mewakili tamu yang diundang ke satu acara.
    """
    id: UUID = Field(alias='guest_id')
    schedule_id: UUID
    user_id: Optional[UUID] = None
    guest_email: Optional[EmailStr] = None
    response_status: RsvpStatus
    role: GuestRole
    
    class Config:
        from_attributes = True
        populate_by_name = True

class ScheduleInstance(BaseModel):
    """
    Model Pydantic untuk Tabel: `ScheduleInstances`
    Mewakili acara yang sudah di-ekspansi (pre-computed).
    Ini adalah KUNCI PERFORMA.
    """
    id: UUID = Field(alias='instance_id')
    schedule_id: UUID
    calendar_id: UUID
    user_id: UUID # <-- Kunci Denormalisasi (MUST FIX)
    start_time: datetime # UTC
    end_time: datetime   # UTC
    is_exception: bool
    is_deleted: bool
    
    class Config:
        from_attributes = True
        populate_by_name = True

# =======================================================================
# LANGKAH 3: MODEL PAYLOAD API (UNTUK VALIDASI INPUT)
# =======================================================================

# --- Resource: Calendars ---

class CalendarCreate(BaseModel):
    """Payload untuk POST /api/v1/calendars"""
    name: str
    # 'owner_user_id' akan diisi oleh dependency
    workspace_id: Optional[UUID] = None # Opsional (jika ini kalender grup)
    visibility: Optional[CalendarVisibility] = CalendarVisibility.private
    metadata: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(extra="forbid")

class CalendarUpdate(BaseModel):
    """Payload untuk PATCH /api/v1/calendars/{id}"""
    name: Optional[str] = None
    visibility: Optional[CalendarVisibility] = None
    metadata: Optional[Dict[str, Any]] = None # Untuk update warna, dll.
    
    model_config = ConfigDict(extra="forbid")

# --- Resource: Schedules ---

class ScheduleCreate(BaseModel):
    """Payload untuk POST /api/v1/calendars/{id}/schedules"""
    title: str
    start_time: datetime
    end_time: datetime
    original_timezone: str = Field(..., description="IANA Timezone (misal: 'Asia/Jakarta'). Wajib untuk konversi UTC.")
    
    rrule: Optional[str] = None
    rdate: Optional[List[datetime]] = None
    exdate: Optional[List[datetime]] = None
    
    metadata: Optional[Dict[str, Any]] = None # Metadata tambahan
    
    model_config = ConfigDict(extra="forbid")

class ScheduleUpdate(BaseModel):
    """Payload untuk PATCH /api/v1/schedules/{id}"""
    title: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    original_timezone: Optional[str] = None
    rrule: Optional[str] = None
    rdate: Optional[List[datetime]] = None
    exdate: Optional[List[datetime]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    # Pilihan untuk mengedit acara berulang
    edit_scope: Optional[Literal["this", "this_and_following"]] = Field(
        None, description="Tentukan cara mengedit acara berulang"
    )
    
    model_config = ConfigDict(extra="forbid")

# --- Resource: Subscriptions ---

class SubscriptionCreate(BaseModel):
    """Payload untuk POST /api/v1/calendars/{id}/subscriptions (Undang orang)"""
    user_id: UUID = Field(..., description="User ID yang akan diundang.")
    role: SubscriptionRole = Field(default=SubscriptionRole.viewer, description="Role yang diberikan.")
    
    model_config = ConfigDict(extra="forbid")

# --- Resource: Guests ---

class GuestCreate(BaseModel):
    """
    Payload untuk POST /api/v1/schedules/{id}/guests
    (Mirip dengan logika invite workspace)
    """
    email: Optional[EmailStr] = Field(None, description="Email tamu eksternal.")
    user_id: Optional[UUID] = Field(None, description="User ID tamu internal.")
    role: Optional[GuestRole] = GuestRole.guest
    
    @model_validator(mode="before")
    def check_email_or_user_id(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback: Memastikan 'email' ATAU 'user_id' disediakan."""
        if not values.get("email") and not values.get("user_id"):
            raise ValueError("Harus menyediakan 'email' atau 'user_id'.")
        if values.get("email") and values.get("user_id"):
             raise ValueError("Hanya boleh menyediakan 'email' atau 'user_id', tidak keduanya.")
        return values
        
    model_config = ConfigDict(extra="forbid")

class GuestRespond(BaseModel):
    """Payload untuk PATCH /api/v1/schedules/{id}/guests/respond (RSVP)"""
    # (Catatan: Endpoint ini mungkin lebih baik di level /invitations/{token})
    # Untuk saat ini, kita asumsikan 'Guest' sudah login
    action: RsvpStatus = Field(..., description="Tindakan: 'accepted' atau 'declined'.")
    
    model_config = ConfigDict(extra="forbid")