from fastapi import APIRouter, Depends
from typing import List
from uuid import UUID

from app.models.workspace import Workspace, WorkspaceCreate
from app.models.user import User
from app.core.dependencies import get_current_user
from app.services.workspace_service import create_new_workspace
from app.db.queries.workspace_queries import get_user_workspaces

router = APIRouter()

@router.post("/", response_model=Workspace, status_code=201)
async def create_workspace(
    workspace_data: WorkspaceCreate,
    current_user: User = Depends(get_current_user)
):
    new_workspace = await create_new_workspace(workspace_data, current_user.id)
    return new_workspace

@router.get("/", response_model=List[Workspace])
async def list_my_workspaces(current_user: User = Depends(get_current_user)):
    return get_user_workspaces(current_user.id)