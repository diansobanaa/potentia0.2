from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class ScheduleCreate(BaseModel):
    title: str
    start_time: datetime
    end_time: datetime
    block_id: Optional[UUID] = None

class Schedule(BaseModel):
    id: UUID
    workspace_id: UUID
    creator_user_id: UUID
    title: str
    start_time: datetime
    end_time: datetime
    rrule: Optional[str]
    block_id: Optional[UUID]
    schedule_metadata: Optional[dict]
    class Config:
        from_attributes = True