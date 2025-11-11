# File: backend/app/db/queries/workspace/workspace_crud.py
# CRUD operations untuk Workspace

import logging
from typing import Dict, Any, Optional
from uuid import UUID
from supabase.client import AsyncClient
from postgrest import APIResponse
from postgrest.exceptions import APIError
from app.core.exceptions import DatabaseError, NotFoundError

logger = logging.getLogger(__name__)


async def create_workspace(
    authed_client: AsyncClient,
    name: str,
    workspace_type: str,
    owner_id: UUID
) -> Dict[str, Any]:
    """
    (Async Native) Membuat Workspace baru di tabel 'Workspaces'.
    """
    try:
        response: APIResponse = await authed_client.table("workspaces").insert({
            "name": name,
            "type": workspace_type,
            "owner_user_id": str(owner_id)
        }, returning="representation").execute()

        if not response or not getattr(response, "data", None):
            logger.error("Gagal membuat workspace — tidak ada response data.")
            raise DatabaseError("create_workspace", "Response kosong dari Supabase.")
        return response.data[0]
    except Exception as e:
        logger.error(f"Error create_workspace (async): {e}", exc_info=True)
        raise DatabaseError("create_workspace", str(e))


async def get_workspace_by_id(
    authed_client: AsyncClient,
    workspace_id: UUID
) -> Optional[dict]:
    """
    (Async Native) Mengambil detail workspace berdasarkan ID.
    """
    try:
        response: APIResponse = await authed_client.table("workspaces") \
            .select("*") \
            .eq("workspace_id", str(workspace_id)) \
            .maybe_single() \
            .execute()

        if response is None:
            logger.warning(
                f"Supabase client mengembalikan None untuk "
                f"get_workspace_by_id {workspace_id}"
            )
            return None

        return response.data if response.data else None

    except APIError as e:
        logger.error(
            f"APIError get_workspace_by_id: {e.message}",
            exc_info=True
        )
        return None
    except Exception as e:
        logger.error(f"Error get_workspace_by_id: {e}", exc_info=True)
        return None


async def update_workspace(
    authed_client: AsyncClient,
    workspace_id: UUID,
    user_id: UUID,
    new_name: str
) -> Dict[str, Any]:
    """
    (Async Native) Memperbarui nama workspace.
    """
    try:
        response = await authed_client.table("workspaces") \
            .update({"name": new_name}, returning="representation") \
            .eq("workspace_id", str(workspace_id)) \
            .eq("owner_user_id", str(user_id)) \
            .execute()

        data = getattr(response, "data", None)
        if not data:
            raise NotFoundError(
                "Workspace tidak ditemukan atau bukan pemilik."
            )
        return data[0]
    except Exception as e:
        if isinstance(e, NotFoundError):
            raise
        raise DatabaseError("update_workspace", str(e))


async def delete_workspace(
    authed_client: AsyncClient,
    workspace_id: UUID,
    user_id: UUID
) -> bool:
    """
    (Async Native) Menghapus workspace.
    Hanya owner yang dapat menghapus workspace.
    """
    try:
        response = await authed_client.table("workspaces") \
            .delete(returning="representation") \
            .eq("workspace_id", str(workspace_id)) \
            .eq("owner_user_id", str(user_id)) \
            .execute()

        data = getattr(response, "data", None)
        if not data:
            return False
        return True
    except Exception as e:
        logger.error(f"Error delete_workspace: {e}", exc_info=True)
        return False

