# File: backend/app/api/v1/endpoints/schedules.py
# (Diperbarui untuk AsyncClient native)

from fastapi import APIRouter, Depends
from typing import List
from uuid import UUID
from app.models.schedule import Schedule
# --- PERBAIKAN: Impor WorkspaceMemberDep (yang sudah async) ---
from app.core.dependencies import WorkspaceMemberDep
# --- PERBAIKAN: Impor kueri async yang baru ---
from app.db.queries.schedule_queries import get_schedules_in_workspace
# --- PERBAIKAN: Impor AsyncClient untuk type hint ---
from supabase.client import AsyncClient

router = APIRouter()

@router.get("/", response_model=List[Schedule])
async def list_schedules_in_workspace(
    workspace_id: UUID,
    # --- PERBAIKAN: 'member_info' sekarang menyediakan AsyncClient ---
    member_info: WorkspaceMemberDep
):
    """
    (Async Native) Mengambil daftar jadwal (legacy) di workspace.
    """
    # 'member_info' (dari WorkspaceMemberDep) sekarang berisi 
    # klien asinkron yang sudah diautentikasi.
    authed_client: AsyncClient = member_info["client"]
    
    # --- PERBAIKAN: Gunakan 'await' pada kueri async ---
    return await get_schedules_in_workspace(authed_client, workspace_id)