from fastapi import APIRouter
from app.api.v1.endpoints import auth, workspaces, canvases, blocks, conversations, schedules

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
api_router.include_router(canvases.router, prefix="/canvases", tags=["canvases"])
api_router.include_router(blocks.router, prefix="/canvases/{canvas_id}/blocks", tags=["blocks"])
api_router.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
api_router.include_router(schedules.router, prefix="/workspaces/{workspace_id}/schedules", tags=["schedules"])