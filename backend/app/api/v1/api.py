# File: backend/app/api/v1/api.py
# (File Diperbarui)

from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth, workspaces, canvases, blocks, schedules,
    chat, canvas_members, workspace_members, invitations,
    calendars, schedules_api, calendar_subscriptions
)
# --- [PENAMBAHAN BARU] ---
from app.api.v1.endpoints import views
from app.api.v1.endpoints import schedule_guests

api_router = APIRouter()

# --- Endpoint Otentikasi & Pengguna ---
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(invitations.router, prefix="/invitations", tags=["invitations"])

# --- Endpoint Workspace & Anggota ---
api_router.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
api_router.include_router(
    workspace_members.router, 
    prefix="/workspaces/{workspace_id}/members",
    tags=["workspaces"] 
)

# --- Endpoint Canvas & Blok ---
api_router.include_router(canvases.router, prefix="/canvases", tags=["canvases"])
api_router.include_router(
    canvas_members.router, 
    prefix="/canvases/{canvas_id}/members",
    tags=["canvases"] 
)
api_router.include_router(blocks.router, prefix="/canvases/{canvas_id}/blocks", tags=["blocks"])

# --- Endpoint Chat ---
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])

# --- [ROUTER BARU UNTUK KALENDER/JADWAL] ---
api_router.include_router(schedules.router, prefix="/workspaces/{workspace_id}/schedules", tags=["schedules (Legacy)"], include_in_schema=False)

api_router.include_router(calendars.router) # (Dari TODO-API-2)
api_router.include_router(schedules_api.router) # (Dari TODO-API-3)
api_router.include_router(calendar_subscriptions.router) # (Dari TODO-API-4)
api_router.include_router(calendar_subscriptions.subscription_delete_router) # (Dari TODO-API-4)
api_router.include_router(schedule_guests.router)# (Dari TODO-API-5)
api_router.include_router(views.router)# (Dari TODO-API-6)