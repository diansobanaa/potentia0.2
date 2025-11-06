import logging
import asyncio
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from app.models.workspace import MemberRole
from supabase import Client
from app.core.exceptions import DatabaseError, NotFoundError

logger = logging.getLogger(__name__)


# ====================================================
#  FUNGSI PEMBUATAN WORKSPACE
# ====================================================
async def create_workspace(authed_client: Client, name: str, workspace_type: str, owner_id: UUID) -> Dict[str, Any]:
    def sync_call():
        try:
            response = authed_client.table("Workspaces").insert({
                "name": name,
                "type": workspace_type,
                "owner_user_id": str(owner_id)
            }, returning="representation").execute()

            if not response or not getattr(response, "data", None):
                logger.error("Gagal membuat workspace — tidak ada response data.")
                raise DatabaseError("create_workspace", "Response kosong dari Supabase.")
            return response.data[0]
        except Exception as e:
            logger.error(f"Error create_workspace: {e}", exc_info=True)
            raise DatabaseError("create_workspace", str(e))
    return await asyncio.to_thread(sync_call)


# ====================================================
#  FUNGSI TAMBAH ANGGOTA
# ====================================================
async def add_member_to_workspace(authed_client: Client, workspace_id: UUID, user_id: UUID, role: MemberRole) -> Dict[str, Any]:
    def sync_call():
        try:
            response = authed_client.table("WorkspaceMembers").insert({
                "workspace_id": str(workspace_id),
                "user_id": str(user_id),
                "role": role.value
            }, returning="representation").execute()

            if not response or not getattr(response, "data", None):
                logger.error("Gagal menambahkan anggota — data kosong.")
                raise DatabaseError("add_member_to_workspace", "Response kosong dari Supabase.")
            return response.data[0]
        except Exception as e:
            logger.error(f"Error add_member_to_workspace: {e}", exc_info=True)
            raise DatabaseError("add_member_to_workspace", str(e))
    return await asyncio.to_thread(sync_call)


# ====================================================
#  AMBIL SEMUA WORKSPACE USER
# ====================================================
async def get_user_workspaces(authed_client: Client, user_id: UUID) -> List[dict]:
    def sync_call():
        try:
            response = authed_client.table("WorkspaceMembers") \
                .select("Workspaces(*)") \
                .eq("user_id", str(user_id)) \
                .execute()

            if not response or not getattr(response, "data", None):
                logger.warning(f"Tidak ada workspace untuk user {user_id}")
                return []
            return [item["Workspaces"] for item in response.data if item.get("Workspaces")]
        except Exception as e:
            logger.error(f"Error get_user_workspaces: {e}", exc_info=True)
            return []
    return await asyncio.to_thread(sync_call)


# ====================================================
#  PAGINASI WORKSPACE
# ====================================================
async def get_user_workspaces_paginated(
    authed_client: Client, user_id: UUID, offset: int, limit: int
) -> Tuple[List[Dict[str, Any]], int]:
    def sync_call() -> Tuple[List[Dict[str, Any]], int]:
        try:
            list_response = authed_client.table("WorkspaceMembers") \
                .select("Workspaces(*)") \
                .eq("user_id", str(user_id)) \
                .order("workspace_id", desc=True) \
                .range(offset, offset + limit - 1) \
                .execute()

            count_response = authed_client.table("WorkspaceMembers") \
                .select("workspace_id", count="exact") \
                .eq("user_id", str(user_id)) \
                .execute()

            data = getattr(list_response, "data", None) or []
            total = getattr(count_response, "count", 0) or 0
            workspaces = [item["Workspaces"] for item in data if item.get("Workspaces")]
            return workspaces, total
        except Exception as e:
            logger.error(f"Error paginating user workspaces: {e}", exc_info=True)
            return [], 0
    return await asyncio.to_thread(sync_call)


# ====================================================
#  AMBIL WORKSPACE BERDASARKAN ID
# ====================================================
async def get_workspace_by_id(authed_client: Client, workspace_id: UUID) -> Optional[dict]:
    def sync_call():
        try:
            response = authed_client.table("Workspaces") \
                .select("*") \
                .eq("workspace_id", str(workspace_id)) \
                .maybe_single() \
                .execute()

            if not response or not getattr(response, "data", None):
                logger.warning(f"Workspace {workspace_id} tidak ditemukan.")
                return None
            return response.data
        except Exception as e:
            logger.error(f"Error get_workspace_by_id: {e}", exc_info=True)
            return None
    return await asyncio.to_thread(sync_call)


# ====================================================
#  PERIKSA KEANGGOTAAN
# ====================================================
async def check_user_membership(authed_client: Client, workspace_id: UUID, user_id: UUID) -> Optional[dict]:
    def sync_call():
        try:
            response = authed_client.table("WorkspaceMembers") \
                .select("*") \
                .eq("workspace_id", str(workspace_id)) \
                .eq("user_id", str(user_id)) \
                .maybe_single() \
                .execute()

            if not response or not getattr(response, "data", None):
                logger.warning(f"User {user_id} bukan anggota workspace {workspace_id}")
                return None
            return response.data
        except Exception as e:
            logger.error(f"Error check_user_membership: {e}", exc_info=True)
            return None
    return await asyncio.to_thread(sync_call)


# ====================================================
#  UPDATE WORKSPACE
# ====================================================
async def update_workspace(
    authed_client: Client, workspace_id: UUID, user_id: UUID, new_name: str
) -> Dict[str, Any]:
    def sync_call():
        try:
            response = authed_client.table("Workspaces") \
                .update({"name": new_name}, returning="representation") \
                .eq("workspace_id", str(workspace_id)) \
                .eq("owner_user_id", str(user_id)) \
                .execute()

            data = getattr(response, "data", None)
            if not data:
                logger.warning(f"Gagal update workspace {workspace_id}, user {user_id} bukan pemilik.")
                raise NotFoundError("Workspace tidak ditemukan atau bukan pemilik.")
            return data[0]
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error update_workspace: {e}", exc_info=True)
            raise DatabaseError("update_workspace", str(e))
    return await asyncio.to_thread(sync_call)


# ====================================================
#  HAPUS WORKSPACE
# ====================================================
async def delete_workspace(
    authed_client: Client, workspace_id: UUID, user_id: UUID
) -> bool:
    def sync_call():
        try:
            response = authed_client.table("Workspaces") \
                .delete(returning="representation") \
                .eq("workspace_id", str(workspace_id)) \
                .eq("owner_user_id", str(user_id)) \
                .execute()

            data = getattr(response, "data", None)
            if not data:
                logger.warning(f"Gagal hapus workspace {workspace_id} — tidak ditemukan atau bukan pemilik.")
                return False
            return True
        except Exception as e:
            logger.error(f"Error delete_workspace: {e}", exc_info=True)
            return False
    return await asyncio.to_thread(sync_call)
