import logging
from uuid import UUID
from typing import Dict, Any, List
from supabase import Client
from app.db.queries.workspace import workspace_queries
from app.models.user import User
from app.models.workspace import (
    WorkspaceCreate, MemberRole, Workspace, WorkspaceUpdate,
    PaginatedWorkspaceListResponse
)
from app.models.user import User
from app.core.exceptions import DatabaseError, NotFoundError


logger = logging.getLogger(__name__)

class WorkspaceService:
    def __init__(self, authed_client: Client, user: User):
        self.client = authed_client
        self.user = user

    async def create_new_workspace(self, workspace_data: WorkspaceCreate) -> Dict[str, Any]:
        # ... (fungsi ini tetap sama) ...
        new_workspace = await workspace_queries.create_workspace(
            self.client, 
            name=workspace_data.name,
            workspace_type=workspace_data.type.value,
            owner_id=self.user.id  
        )
        if new_workspace:
            await workspace_queries.add_member_to_workspace(
                self.client, 
                workspace_id=new_workspace["workspace_id"],
                user_id=self.user.id, 
                role=MemberRole.admin
            )
        return new_workspace

    async def get_user_workspaces_list(self) -> List[Dict[str, Any]]:
        """Mengambil daftar workspace milik pengguna (NON-PAGINATED)."""
        return await workspace_queries.get_user_workspaces(self.client, self.user.id)

    # --- [FUNGSI BARU UNTUK PAGINASI] ---
    async def get_paginated_user_workspaces(
        self, page: int, size: int
    ) -> PaginatedWorkspaceListResponse:
        """Mengambil daftar workspace milik pengguna (PAGINASI)."""
        offset = (page - 1) * size
        user_id = self.user.id
        logger.info(f"User {user_id} mengambil daftar workspace: page {page}, size {size}")

        # Memanggil fungsi _paginated yang baru dari Langkah 2
        workspaces_data, total = await workspace_queries.get_user_workspaces_paginated(
            self.client, user_id, offset, size
        )
        
        # Validasi data ke model Pydantic
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
        # ... (fungsi ini tetap sama) ...
        data = await workspace_queries.get_workspace_by_id(self.client, workspace_id)
        if not data:
            raise NotFoundError("Workspace tidak ditemukan.")
        return data

    async def update_workspace_details(
        self, workspace_id: UUID, update_data: WorkspaceUpdate
    ) -> Dict[str, Any]:
        # ... (fungsi ini tetap sama) ...
        return await workspace_queries.update_workspace(
            self.client, workspace_id, self.user.id, update_data.name
        )

    async def delete_workspace(self, workspace_id: UUID) -> bool:
        # ... (fungsi ini tetap sama) ...
        return await workspace_queries.delete_workspace(
            self.client, workspace_id, self.user.id
        )
    

