# File: backend/app/db/queries/workspace/workspace_queries.py
# (Diperbarui untuk AsyncClient native dan asyncio.gather)

import logging
import asyncio
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
import secrets 
# --- PERBAIKAN: Impor AsyncClient ---
from supabase.client import AsyncClient
from postgrest import APIResponse
from postgrest.exceptions import APIError
from app.models.user import User
from app.models.workspace import MemberRole, InvitationType
from app.core.exceptions import DatabaseError, NotFoundError

logger = logging.getLogger(__name__)

# ====================================================
#  FUNGSI CRUD WORKSPACE (Induk)
# ====================================================

async def create_workspace(
    authed_client: AsyncClient, # <-- Tipe diubah
    name: str, 
    workspace_type: str, 
    owner_id: UUID
) -> Dict[str, Any]:
    """
    (Async Native) Membuat Workspace baru di tabel 'Workspaces'.
    """
    try:
        response: APIResponse = await authed_client.table("Workspaces").insert({ # <-- 'await'
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
    authed_client: AsyncClient, # <-- Tipe diubah
    workspace_id: UUID
) -> Optional[dict]:
    """
    (Async Native) Mengambil detail workspace berdasarkan ID.
    """
    try:
        response: APIResponse = await authed_client.table("Workspaces") \
            .select("*") \
            .eq("workspace_id", str(workspace_id)) \
            .maybe_single() \
            .execute() # <-- 'await'
        
        if response is None:
            logger.warning(f"Supabase client mengembalikan None untuk get_workspace_by_id {workspace_id}")
            return None
        
        return response.data if response.data else None
        
    except APIError as e:
        logger.error(f"APIError get_workspace_by_id: {e.message}", exc_info=True)
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
    try:
        # --- PERBAIKAN: Hapus .single() ---
        response = await authed_client.table("Workspaces") \
            .update({"name": new_name}, returning="representation") \
            .eq("workspace_id", str(workspace_id)) \
            .eq("owner_user_id", str(user_id)) \
            .execute()
        # ---------------------------------
        data = getattr(response, "data", None)
        if not data:
            raise NotFoundError("Workspace tidak ditemukan atau bukan pemilik.")
        return data[0]
    except Exception as e:
        if isinstance(e, NotFoundError): raise
        raise DatabaseError("update_workspace", str(e))

async def delete_workspace(
    authed_client: AsyncClient, 
    workspace_id: UUID, 
    user_id: UUID
) -> bool:
    try:
        # --- PERBAIKAN: Hapus .single() ---
        response = await authed_client.table("Workspaces") \
            .delete(returning="representation") \
            .eq("workspace_id", str(workspace_id)) \
            .eq("owner_user_id", str(user_id)) \
            .execute()
        # ---------------------------------
        data = getattr(response, "data", None)
        if not data:
            return False
        return True
    except Exception as e:
        return False

# ====================================================
#  FUNGSI PAGINASI WORKSPACE (List)
# ====================================================

async def get_user_workspaces_paginated(
    authed_client: AsyncClient, # <-- Tipe diubah
    user_id: UUID, 
    offset: int, 
    limit: int
) -> Tuple[List[Dict[str, Any]], int]:
    """
    (Async Native) Mengambil daftar workspace dengan paginasi.
    """
    try:
        # --- PERBAIKAN: Optimasi dengan asyncio.gather ---
        
        # Kueri 1: Ambil data paginasi
        list_task = authed_client.table("WorkspaceMembers") \
            .select("Workspaces(*)") \
            .eq("user_id", str(user_id)) \
            .order("workspace_id", desc=True) \
            .range(offset, offset + limit - 1) \
            .execute() # (awaitable)

        # Kueri 2: Ambil total hitungan (count)
        count_task = authed_client.table("WorkspaceMembers") \
            .select("workspace_id", count="exact") \
            .eq("user_id", str(user_id)) \
            .execute() # (awaitable)

        # Jalankan kueri secara paralel
        list_response, count_response = await asyncio.gather(
            list_task,
            count_task
        )
        # ---------------------------------------------

        data = getattr(list_response, "data", None) or []
        total = getattr(count_response, "count", 0) or 0
        
        workspaces = [item["Workspaces"] for item in data if item.get("Workspaces")]
        return workspaces, total
    except Exception as e:
        logger.error(f"Error paginating user workspaces (async): {e}", exc_info=True)
        return [], 0 # Kembalikan list kosong saat error

# ====================================================
#  FUNGSI CRUD ANGGOTA WORKSPACE
# ====================================================

async def check_user_membership(
    authed_client: AsyncClient, # <-- Tipe diubah
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
            .execute() # <-- 'await'

        if response is None:
            logger.error(f"Supabase client mengembalikan None saat cek keanggotaan (W:{workspace_id}, U:{user_id})")
            return None
            
        if not response.data:
            logger.warning(f"User {user_id} bukan anggota workspace {workspace_id}")
            return None
        
        return response.data
        
    except APIError as e:
        logger.error(f"APIError check_user_membership (W:{workspace_id}, U:{user_id}): {e.message}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Error check_user_membership (W:{workspace_id}, U:{user_id}): {e}", exc_info=True)
        return None

async def add_member_to_workspace(authed_client: AsyncClient, workspace_id: UUID, user_id: UUID, role: MemberRole) -> Dict[str, Any]:
    payload = {"workspace_id": str(workspace_id), "user_id": str(user_id), "role": role.value}
    try:
        # (Upsert sudah benar)
        response = await authed_client.table("WorkspaceMembers") \
            .upsert(payload, on_conflict="workspace_id, user_id", returning="representation") \
            .execute()
        if not response or not getattr(response, "data", None):
            raise DatabaseError("add_member_to_workspace", "Response kosong dari Supabase.")
        return response.data[0]
    except Exception as e:
        if "foreign key constraint" in str(e): raise NotFoundError("Gagal menambahkan anggota.")
        raise DatabaseError("add_member_to_workspace", str(e))
    
async def create_workspace_invitation(
    authed_client: AsyncClient, # <-- Tipe diubah
    workspace_id: UUID,
    inviter_id: UUID,
    role: MemberRole,
    invitee_email: Optional[str] = None,
    invitee_user_id: Optional[UUID] = None
) -> Dict[str, Any]:
    """
    (Async Native) Membuat undangan baru di 'WorkspaceInvitations'.
    """
    try:
        invitation_payload = {
            "workspace_id": str(workspace_id),
            "inviter_user_id": str(inviter_id),
            "role": role.value,
            "status": "pending",
            "token": secrets.token_urlsafe(32),
        }

        if invitee_user_id:
            logger.debug(f"Menyiapkan Invite by ID untuk user {invitee_user_id}")
            invitation_payload["invitee_user_id"] = str(invitee_user_id)
            invitation_payload["type"] = InvitationType.USER_ID.value

            # --- PERBAIKAN: Panggilan DB paralel ---
            member_check_task = authed_client.table("WorkspaceMembers").select("id").eq("workspace_id", str(workspace_id)).eq("user_id", str(invitee_user_id)).execute()
            pending_check_task = authed_client.table("WorkspaceInvitations").select("invitation_id").eq("workspace_id", str(workspace_id)).eq("invitee_user_id", str(invitee_user_id)).eq("status", "pending").execute()
            member_check, pending_check = await asyncio.gather(member_check_task, pending_check_task)
            
            if member_check.data:
                raise DatabaseError("invite_conflict", "Pengguna ini sudah menjadi anggota workspace.")
            if pending_check.data:
                raise DatabaseError("invite_conflict", "Pengguna ini sudah memiliki undangan yang tertunda (pending).")

        elif invitee_email:
            logger.debug(f"Menyiapkan Invite by Email untuk {invitee_email}")
            invitation_payload["invitee_email"] = invitee_email
            invitation_payload["type"] = InvitationType.EMAIL.value
            
            # --- PERBAIKAN: Panggilan DB paralel ---
            member_check_task = authed_client.table("WorkspaceMembers").select("user:user_id(email)").eq("workspace_id", str(workspace_id)).execute()
            pending_check_task = authed_client.table("WorkspaceInvitations").select("invitation_id").eq("workspace_id", str(workspace_id)).eq("invitee_email", invitee_email).eq("status", "pending").execute()
            member_check, pending_check = await asyncio.gather(member_check_task, pending_check_task)

            if member_check.data:
                for member in member_check.data:
                    if member.get("user") and member["user"].get("email") == invitee_email:
                        raise DatabaseError("invite_conflict", "Pengguna dengan email ini sudah menjadi anggota workspace.")
            if pending_check.data:
                raise DatabaseError("invite_conflict", "Pengguna dengan email ini sudah memiliki undangan yang tertunda (pending).")
        
        else:
             raise ValueError("Harus menyediakan invitee_email atau invitee_user_id.")

        response: APIResponse = await authed_client.table("WorkspaceInvitations") \
            .insert(invitation_payload, returning="representation") \
            .execute() # <-- 'await'
        
        if not response.data:
            raise DatabaseError("invite_create_fail", "Gagal membuat undangan di database.")
            
        return response.data[0]
        
    except APIError as e:
        error_msg = getattr(e, 'message', str(e))
        logger.error(
            f"APIError create_workspace_invitation (async): {error_msg}",
            exc_info=True
        )
        # Check for conflict errors in error message
        error_str = str(e).lower() + error_msg.lower()
        if "invite_conflict" in error_str or "already exists" in error_str:
            raise DatabaseError(
                "invite_conflict",
                "Pengguna ini sudah memiliki undangan atau sudah menjadi anggota."
            )
        raise DatabaseError("invite_create_async_api", error_msg)
    except (DatabaseError, NotFoundError, ValueError) as e:
        # Re-raise known exceptions as-is
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(
            f"Error create_workspace_invitation (async): {error_msg}",
            exc_info=True
        )
        raise DatabaseError("invite_create_async_general", error_msg)

async def list_workspace_members(
    authed_client: AsyncClient, # <-- Tipe diubah
    workspace_id: UUID
) -> List[Dict[str, Any]]:
    """
    (Async Native) Mengambil daftar anggota.
    """
    try:
        response: APIResponse = await authed_client.table("WorkspaceMembers") \
            .select("role, user:user_id(user_id, name, email)") \
            .eq("workspace_id", str(workspace_id)) \
            .execute() # <-- 'await'
        return response.data if response.data else []
    except Exception as e:
        logger.error(f"Error list_workspace_members (async) {workspace_id}: {e}", exc_info=True)
        raise DatabaseError("list_workspace_members_async", str(e))

async def update_workspace_member_role(
    authed_client: AsyncClient, 
    workspace_id: UUID, 
    user_id_to_update: UUID, 
    new_role: MemberRole
) -> Dict[str, Any]:
    try:
        workspace = await authed_client.table("Workspaces").select("owner_user_id").eq("workspace_id", str(workspace_id)).maybe_single().execute()
        if not workspace or not workspace.data:
             raise NotFoundError("Workspace tidak ditemukan.")
        owner_id = workspace.data.get("owner_user_id")
        if str(user_id_to_update) == str(owner_id) and new_role != MemberRole.admin:
            raise DatabaseError("owner_demote_prevented", "Pemilik (Owner) workspace harus selalu menjadi Admin.")

        # --- PERBAIKAN: Hapus .single() ---
        response: APIResponse = await (
            authed_client.table("WorkspaceMembers")
            .update({"role": new_role.value}, returning="representation")
            .eq("workspace_id", str(workspace_id))
            .eq("user_id", str(user_id_to_update))
            .execute()
        )
        # ---------------------------------
        if not response.data or len(response.data) == 0:
            raise NotFoundError(f"Anggota dengan ID {user_id_to_update} tidak ditemukan.")
        return response.data[0]
    except Exception as e:
        if isinstance(e, (DatabaseError, NotFoundError)): raise
        raise DatabaseError("update_role_async", str(e))
    
async def remove_workspace_member(
    authed_client: AsyncClient, 
    workspace_id: UUID, 
    user_id_to_remove: UUID
) -> bool:
    try:
        workspace = await authed_client.table("Workspaces").select("owner_user_id").eq("workspace_id", str(workspace_id)).maybe_single().execute()
        if not workspace or not workspace.data:
             raise NotFoundError("Workspace tidak ditemukan.")
        owner_id = workspace.data.get("owner_user_id")
        if str(user_id_to_remove) == str(owner_id):
            raise DatabaseError("owner_remove_prevented", "Pemilik (Owner) workspace tidak dapat dihapus.")

        # --- PERBAIKAN: Hapus .single() ---
        response: APIResponse = await (
            authed_client.table("WorkspaceMembers")
            .delete(returning="representation")
            .eq("workspace_id", str(workspace_id))
            .eq("user_id", str(user_id_to_remove))
            .execute()
        )
        # ---------------------------------
        if not response.data or len(response.data) == 0:
            raise NotFoundError(f"Anggota dengan ID {user_id_to_remove} tidak ditemukan.")
        return True
    except Exception as e:
        if isinstance(e, (DatabaseError, NotFoundError)): raise
        raise DatabaseError("remove_member_async", str(e))
        
# ====================================================
#  FUNGSI LOGIKA UNDANGAN
# ====================================================

async def _find_invitation_by_token(
    authed_client: AsyncClient, # <-- Tipe diubah
    token: str
) -> Optional[Dict[str, Any]]:
    """Helper ASYNC: Mengambil undangan 'pending' berdasarkan token."""
    try:
        response: APIResponse = await authed_client.table("WorkspaceInvitations") \
            .select("*") \
            .eq("token", token) \
            .eq("status", "pending") \
            .maybe_single() \
            .execute() # <-- 'await'
            
        if response is None: return None
        return response.data if response.data else None
    except Exception as e:
        logger.error(f"Error di _find_invitation_by_token (async): {e}", exc_info=True)
        return None

async def _delete_invitation_by_token(
    authed_client: AsyncClient, # <-- Tipe diubah
    token: str
) -> bool:
    """Helper ASYNC: Menghapus undangan setelah diproses."""
    try:
        await authed_client.table("WorkspaceInvitations") \
            .delete() \
            .eq("token", token) \
            .execute() # <-- 'await'
        return True
    except Exception as e:
        logger.error(f"Error di _delete_invitation_by_token (async): {e}", exc_info=True)
        return False

async def respond_to_workspace_invitation(
    authed_client: AsyncClient, # <-- Tipe diubah
    token: str,
    action: str, 
    user: User
) -> Optional[Dict[str, Any]]:
    """
    (Async Native) Orkestrator Logika untuk menerima atau menolak undangan.
    """
    
    invitation = await _find_invitation_by_token(authed_client, token)
    
    if not invitation:
        raise NotFoundError("Undangan ini tidak valid atau telah kedaluwarsa.")

    invitee_email = invitation.get("invitee_email")
    invitee_user_id = invitation.get("invitee_user_id")
    
    if invitee_email and invitee_email.lower() != user.email.lower():
        raise DatabaseError("invite_permission_denied", "Undangan ini ditujukan untuk alamat email yang berbeda.")
    if invitee_user_id and str(invitee_user_id) != str(user.id):
        raise DatabaseError("invite_permission_denied", "Undangan ini ditujukan untuk pengguna yang berbeda.")

    workspace_id = invitation.get("workspace_id")
    role = invitation.get("role", "guest") 

    await _delete_invitation_by_token(authed_client, token)

    if action == "reject":
        logger.info(f"Pengguna {user.id} menolak undangan ke workspace {workspace_id}")
        return {"status": "rejected"}
    
    if action == "accept":
        logger.info(f"Pengguna {user.id} menerima undangan ke workspace {workspace_id} sebagai {role}")
        
        # Panggil fungsi 'add_member_to_workspace' yang sekarang async
        new_member_data = await add_member_to_workspace(
            authed_client=authed_client,
            workspace_id=UUID(workspace_id),
            user_id=user.id,
            role=MemberRole(role)
        )
        return new_member_data
        
    return None