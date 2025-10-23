from fastapi import APIRouter, Depends
from typing import List
from uuid import UUID

from app.models.workspace import Workspace, WorkspaceCreate
from app.models.user import User
from app.core.dependencies import get_current_user_and_client # <-- Gunakan dependency baru
from app.services.workspace_service import create_new_workspace
from app.db.queries.workspace_queries import get_user_workspaces

router = APIRouter()

@router.post("/", response_model=Workspace, status_code=201)
async def create_workspace(
    workspace_data: WorkspaceCreate,
    # Ganti 'get_current_user' dengan 'get_current_user_and_client'
    auth_info: dict = Depends(get_current_user_and_client) 
):
    user = auth_info["user"]
    authed_client = auth_info["client"] # Ambil klien baru
    
    # Teruskan kliennya ke fungsi service/query
    new_workspace = await create_new_workspace(authed_client, workspace_data, user.id) 
    return new_workspace

@router.get("/", response_model=List[Workspace])
async def list_my_workspaces(
    auth_info: dict = Depends(get_current_user_and_client) # Ganti juga di sini
):
    user = auth_info["user"]
    authed_client = auth_info["client"] # Ambil klien baru

    # Teruskan kliennya ke fungsi query
    return get_user_workspaces(authed_client, user.id)