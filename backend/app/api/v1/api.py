from fastapi import APIRouter
from app.api.v1.endpoints import auth, workspaces, canvases, blocks, schedules
from app.api.v1.endpoints import chat

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
api_router.include_router(canvases.router, prefix="/canvases", tags=["canvases"])
api_router.include_router(blocks.router, prefix="/canvases/{canvas_id}/blocks", tags=["blocks"])
api_router.include_router(schedules.router, prefix="/workspaces/{workspace_id}/schedules", tags=["schedules"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])