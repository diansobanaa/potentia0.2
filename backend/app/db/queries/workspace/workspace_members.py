# File: backend/app/db/queries/workspace/workspace_members.py
# CRUD operations untuk Workspace Members

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from supabase.client import AsyncClient
from postgrest import APIResponse
from postgrest.exceptions import APIError
from app.models.workspace import MemberRole
from app.core.exceptions import DatabaseError, NotFoundError

logger = logging.getLogger(__name__)


async def check_user_membership(
    authed_client: AsyncClient,
    workspace_id: UUID,
    user_id: UUID
) -> Optional[dict]:
    """
    (Async Native) Memeriksa apakah pengguna adalah anggota workspace.
    """
    try:
        response: APIResponse = await authed_client.table("WorkspaceMembers") \
            .select("*") \
            .eq("workspace_id", str(workspace_id)) \
            .eq("user_id", str(user_id)) \
            .maybe_single() \
            .execute()

        if response is None:
            logger.error(
                f"Supabase client mengembalikan None saat cek keanggotaan "
                f"(W:{workspace_id}, U:{user_id})"
            )
            return None

        if not response.data:
            logger.warning(
                f"User {user_id} bukan anggota workspace {workspace_id}"
            )
            return None

        return response.data

    except APIError as e:
        logger.error(
            f"APIError check_user_membership "
            f"(W:{workspace_id}, U:{user_id}): {e.message}",
            exc_info=True
        )
        return None
    except Exception as e:
        logger.error(
            f"Error check_user_membership "
            f"(W:{workspace_id}, U:{user_id}): {e}",
            exc_info=True
        )
        return None


async def add_member_to_workspace(
    authed_client: AsyncClient,
    workspace_id: UUID,
    user_id: UUID,
    role: MemberRole
) -> Dict[str, Any]:
    """
    (Async Native) Menambahkan anggota ke workspace.
    Menggunakan upsert untuk menghindari duplicate.
    """
    payload = {
        "workspace_id": str(workspace_id),
        "user_id": str(user_id),
        "role": role.value
    }
    try:
        response = await authed_client.table("WorkspaceMembers") \
            .upsert(
                payload,
                on_conflict="workspace_id, user_id",
                returning="representation"
            ) \
            .execute()

        if not response or not getattr(response, "data", None):
            raise DatabaseError(
                "add_member_to_workspace",
                "Response kosong dari Supabase."
            )
        return response.data[0]
    except Exception as e:
        if "foreign key constraint" in str(e):
            raise NotFoundError("Gagal menambahkan anggota.")
        raise DatabaseError("add_member_to_workspace", str(e))


async def list_workspace_members(
    authed_client: AsyncClient,
    workspace_id: UUID
) -> List[Dict[str, Any]]:
    """
    (Async Native) Mengambil daftar anggota workspace.
    """
    try:
        response: APIResponse = await authed_client.table("WorkspaceMembers") \
            .select("role, user:user_id(user_id, name, email)") \
            .eq("workspace_id", str(workspace_id)) \
            .execute()

        return response.data if response.data else []
    except Exception as e:
        logger.error(
            f"Error list_workspace_members (async) {workspace_id}: {e}",
            exc_info=True
        )
        raise DatabaseError("list_workspace_members_async", str(e))


async def update_workspace_member_role(
    authed_client: AsyncClient,
    workspace_id: UUID,
    user_id_to_update: UUID,
    new_role: MemberRole
) -> Dict[str, Any]:
    """
    (Async Native) Memperbarui role anggota workspace.
    Mencegah owner di-demote dari admin.
    """
    try:
        workspace = await authed_client.table("Workspaces") \
            .select("owner_user_id") \
            .eq("workspace_id", str(workspace_id)) \
            .maybe_single() \
            .execute()

        if not workspace or not workspace.data:
            raise NotFoundError("Workspace tidak ditemukan.")

        owner_id = workspace.data.get("owner_user_id")
        if (str(user_id_to_update) == str(owner_id) and
                new_role != MemberRole.admin):
            raise DatabaseError(
                "owner_demote_prevented",
                "Pemilik (Owner) workspace harus selalu menjadi Admin."
            )

        response: APIResponse = await (
            authed_client.table("WorkspaceMembers")
            .update({"role": new_role.value}, returning="representation")
            .eq("workspace_id", str(workspace_id))
            .eq("user_id", str(user_id_to_update))
            .execute()
        )

        if not response.data or len(response.data) == 0:
            raise NotFoundError(
                f"Anggota dengan ID {user_id_to_update} tidak ditemukan."
            )
        return response.data[0]
    except Exception as e:
        if isinstance(e, (DatabaseError, NotFoundError)):
            raise
        raise DatabaseError("update_role_async", str(e))


async def remove_workspace_member(
    authed_client: AsyncClient,
    workspace_id: UUID,
    user_id_to_remove: UUID
) -> bool:
    """
    (Async Native) Menghapus anggota dari workspace.
    Mencegah owner dihapus dari workspace.
    """
    try:
        workspace = await authed_client.table("Workspaces") \
            .select("owner_user_id") \
            .eq("workspace_id", str(workspace_id)) \
            .maybe_single() \
            .execute()

        if not workspace or not workspace.data:
            raise NotFoundError("Workspace tidak ditemukan.")

        owner_id = workspace.data.get("owner_user_id")
        if str(user_id_to_remove) == str(owner_id):
            raise DatabaseError(
                "owner_remove_prevented",
                "Pemilik (Owner) workspace tidak dapat dihapus."
            )

        response: APIResponse = await (
            authed_client.table("WorkspaceMembers")
            .delete(returning="representation")
            .eq("workspace_id", str(workspace_id))
            .eq("user_id", str(user_id_to_remove))
            .execute()
        )

        if not response.data or len(response.data) == 0:
            raise NotFoundError(
                f"Anggota dengan ID {user_id_to_remove} tidak ditemukan."
            )
        return True
    except Exception as e:
        if isinstance(e, (DatabaseError, NotFoundError)):
            raise
        raise DatabaseError("remove_member_async", str(e))

