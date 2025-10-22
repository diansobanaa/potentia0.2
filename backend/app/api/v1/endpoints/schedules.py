from fastapi import APIRouter, Depends
from typing import List
from uuid import UUID
from app.models.schedule import Schedule
from app.core.dependencies import get_current_workspace_member
from app.db.queries.schedule_queries import get_schedules_in_workspace

router = APIRouter()

@router.get("/", response_model=List[Schedule])
async def list_schedules_in_workspace(
    workspace_id: UUID,
    member_info: dict = Depends(get_current_workspace_member)
):
    return get_schedules_in_workspace(workspace_id)