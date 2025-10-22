from fastapi import APIRouter, Depends, HTTPException
from typing import List
from uuid import UUID

from app.models.canvas import Canvas, CanvasCreate
from app.models.user import User
from app.core.dependencies import get_current_user, get_current_workspace_member
from app.db.queries.canvas_queries import create_canvas, get_canvases_in_workspace, get_user_personal_canvases

router = APIRouter()

@router.post("/workspace/{workspace_id}", response_model=Canvas, status_code=201)
async def create_canvas_in_workspace(
    workspace_id: UUID,
    canvas_data: CanvasCreate,
    member_info: dict = Depends(get_current_workspace_member)
):
    current_user = member_info["user"]
    new_canvas = create_canvas(canvas_data.title, canvas_data.icon, workspace_id, current_user.id, None)
    return new_canvas

@router.post("/personal", response_model=Canvas, status_code=201)
async def create_personal_canvas(
    canvas_data: CanvasCreate,
    current_user: User = Depends(get_current_user)
):
    new_canvas = create_canvas(canvas_data.title, canvas_data.icon, None, current_user.id, current_user.id)
    return new_canvas

@router.get("/workspace/{workspace_id}", response_model=List[Canvas])
async def list_canvases_in_workspace(
    workspace_id: UUID,
    member_info: dict = Depends(get_current_workspace_member)
):
    return get_canvases_in_workspace(workspace_id)

@router.get("/personal", response_model=List[Canvas])
async def list_personal_canvases(current_user: User = Depends(get_current_user)):
    return get_user_personal_canvases(current_user.id)