# backend/app/services/workspace/workspace_service.py
# (Diperbarui untuk AsyncClient native)

import logging
from uuid import UUID
from typing import Dict, Any, List
# --- PERBAIKAN: Impor AsyncClient ---
from supabase.client import AsyncClient
# ------------------------------------
from app.db.queries.workspace import (
    create_workspace,
    get_workspace_by_id,
    update_workspace,
    delete_workspace,
    get_user_workspaces_paginated,
    add_member_to_workspace
)
from app.models.user import User
from app.models.workspace import (
    WorkspaceCreate, MemberRole, Workspace, WorkspaceUpdate,
    PaginatedWorkspaceListResponse
)
from app.core.exceptions import DatabaseError, NotFoundError

logger = logging.getLogger(__name__)

class WorkspaceService:
    def __init__(self, authed_client: AsyncClient, user: User): # <-- Tipe diubah
        self.client = authed_client
        self.user = user

    async def create_new_workspace(self, workspace_data: WorkspaceCreate) -> Dict[str, Any]:
        """(Async Native) Membuat workspace baru."""
        
        # --- PERBAIKAN: Panggilan 'await' langsung ---
        new_workspace = await create_workspace(
            self.client, 
            name=workspace_data.name,
            workspace_type=workspace_data.type.value,
            owner_id=self.user.id  
        )
        if new_workspace:
            await add_member_to_workspace(
                self.client, 
                workspace_id=new_workspace["workspace_id"],
                user_id=self.user.id, 
                role=MemberRole.admin
            )
        # ---------------------------------------------
        return new_workspace

    # (Fungsi 'get_user_workspaces_list' yang lama dihapus karena sudah ada versi paginasi)
    
    async def get_paginated_user_workspaces(
        self, page: int, size: int
    ) -> PaginatedWorkspaceListResponse:
        """(Async Native) Mengambil daftar workspace (PAGINASI)."""
        offset = (page - 1) * size
        user_id = self.user.id
        logger.info(f"User {user_id} mengambil daftar workspace: page {page}, size {size}")

        # --- PERBAIKAN: Panggilan 'await' langsung ---
        # (Kueri ini sudah dioptimalkan dengan asyncio.gather)
        workspaces_data, total = await get_user_workspaces_paginated(
            self.client, user_id, offset, size
        )
        # ---------------------------------------------
        
        workspace_items = [Workspace.model_validate(w) for w in workspaces_data]
        total_pages = (total + size - 1) // size

        return PaginatedWorkspaceListResponse(
            items=workspace_items,
            total=total,
            page=page,
            size=size,
            total_pages=total_pages
        )

    async def get_workspace_details(self, workspace_id: UUID) -> Dict[str, Any]:
        """(Async Native) Mengambil detail workspace."""
        # --- PERBAIKAN: Panggilan 'await' langsung ---
        data = await get_workspace_by_id(self.client, workspace_id)
        if not data:
            raise NotFoundError("Workspace tidak ditemukan.")
        return data

    async def update_workspace_details(
        self, workspace_id: UUID, update_data: WorkspaceUpdate
    ) -> Dict[str, Any]:
        """(Async Native) Memperbarui detail workspace."""
        # --- PERBAIKAN: Panggilan 'await' langsung ---
        return await update_workspace(
            self.client, workspace_id, self.user.id, update_data.name
        )

    async def delete_workspace(self, workspace_id: UUID) -> bool:
        """(Async Native) Menghapus workspace."""
        # --- PERBAIKAN: Panggilan 'await' langsung ---
        return await delete_workspace(
            self.client, workspace_id, self.user.id
        )