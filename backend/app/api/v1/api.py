# File: backend/app/api/v1/api.py
# (Diperbarui untuk Fase 4)

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    blocks,
    calendars,
    calendar_subscriptions,
    canvases,
    chat,
    chat_actions, # <-- [BARU] Impor
    health, 
    invitations,
    notifications,
    schedules,
    schedules_api,
    schedule_guests,
    views,
    workspaces,
    workspace_members,
    socket,
)

api_router = APIRouter()

api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(blocks.router, prefix="/blocks", tags=["blocks"])
api_router.include_router(calendars.router, prefix="/calendars", tags=["calendars"])
api_router.include_router(calendar_subscriptions.router, prefix="/calendar_subscriptions", tags=["calendar_subscriptions"])
api_router.include_router(canvases.router) 
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(chat_actions.router) # <-- [BARU] Daftarkan router
api_router.include_router(health.router, tags=["health"]) 
api_router.include_router(invitations.router, prefix="/invitations", tags=["invitations"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(schedules.router, prefix="/schedules", tags=["schedules"])
api_router.include_router(schedules_api.router, prefix="/schedules_api", tags=["schedules_api"])
api_router.include_router(schedule_guests.router, prefix="/schedule_guests", tags=["schedule_guests"])
api_router.include_router(views.router, prefix="/views", tags=["views"])
api_router.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
api_router.include_router(workspace_members.router, prefix="/workspace_members", tags=["workspace_members"])
api_router.include_router(socket.router, tags=["websocket"])