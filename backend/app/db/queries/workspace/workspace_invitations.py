# File: backend/app/db/queries/workspace/workspace_invitations.py
# Operations untuk Workspace Invitations

import logging
import asyncio
import secrets
from typing import Dict, Any, Optional
from uuid import UUID
from supabase.client import AsyncClient
from postgrest import APIResponse
from postgrest.exceptions import APIError
from app.models.user import User
from app.models.workspace import MemberRole, InvitationType
from app.core.exceptions import DatabaseError, NotFoundError

logger = logging.getLogger(__name__)


async def create_workspace_invitation(
    authed_client: AsyncClient,
    workspace_id: UUID,
    inviter_id: UUID,
    role: MemberRole,
    invitee_email: Optional[str] = None,
    invitee_user_id: Optional[UUID] = None
) -> Dict[str, Any]:
    """
    (Async Native) Membuat undangan baru di 'WorkspaceInvitations'.

    Mendukung dua tipe undangan:
    1. Via user_id: untuk user yang sudah terdaftar
    2. Via email: untuk user eksternal
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
            logger.debug(
                f"Menyiapkan Invite by ID untuk user {invitee_user_id}"
            )
            invitation_payload["invitee_user_id"] = str(invitee_user_id)
            invitation_payload["type"] = InvitationType.USER_ID.value

            # Panggilan DB paralel untuk optimasi
            member_check_task = authed_client.table("WorkspaceMembers") \
                .select("id") \
                .eq("workspace_id", str(workspace_id)) \
                .eq("user_id", str(invitee_user_id)) \
                .execute()

            pending_check_task = authed_client.table(
                "WorkspaceInvitations"
            ) \
                .select("invitation_id") \
                .eq("workspace_id", str(workspace_id)) \
                .eq("invitee_user_id", str(invitee_user_id)) \
                .eq("status", "pending") \
                .execute()

            member_check, pending_check = await asyncio.gather(
                member_check_task, pending_check_task
            )

            if member_check.data:
                raise DatabaseError(
                    "invite_conflict",
                    "Pengguna ini sudah menjadi anggota workspace."
                )
            if pending_check.data:
                raise DatabaseError(
                    "invite_conflict",
                    "Pengguna ini sudah memiliki undangan yang tertunda "
                    "(pending)."
                )

        elif invitee_email:
            logger.debug(
                f"Menyiapkan Invite by Email untuk {invitee_email}"
            )
            invitation_payload["invitee_email"] = invitee_email
            invitation_payload["type"] = InvitationType.EMAIL.value

            # Panggilan DB paralel untuk optimasi
            member_check_task = authed_client.table("WorkspaceMembers") \
                .select("user:user_id(email)") \
                .eq("workspace_id", str(workspace_id)) \
                .execute()

            pending_check_task = authed_client.table(
                "WorkspaceInvitations"
            ) \
                .select("invitation_id") \
                .eq("workspace_id", str(workspace_id)) \
                .eq("invitee_email", invitee_email) \
                .eq("status", "pending") \
                .execute()

            member_check, pending_check = await asyncio.gather(
                member_check_task, pending_check_task
            )

            if member_check.data:
                for member in member_check.data:
                    if (member.get("user") and
                            member["user"].get("email") == invitee_email):
                        raise DatabaseError(
                            "invite_conflict",
                            "Pengguna dengan email ini sudah menjadi "
                            "anggota workspace."
                        )
            if pending_check.data:
                raise DatabaseError(
                    "invite_conflict",
                    "Pengguna dengan email ini sudah memiliki undangan "
                    "yang tertunda (pending)."
                )

        else:
            raise ValueError(
                "Harus menyediakan invitee_email atau invitee_user_id."
            )

        response: APIResponse = await authed_client.table(
            "WorkspaceInvitations"
        ) \
            .insert(invitation_payload, returning="representation") \
            .execute()

        if not response.data:
            raise DatabaseError(
                "invite_create_fail",
                "Gagal membuat undangan di database."
            )

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
                "Pengguna ini sudah memiliki undangan atau sudah menjadi "
                "anggota."
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


async def _find_invitation_by_token(
    authed_client: AsyncClient,
    token: str
) -> Optional[Dict[str, Any]]:
    """
    Helper ASYNC: Mengambil undangan 'pending' berdasarkan token.
    """
    try:
        response: APIResponse = await authed_client.table(
            "WorkspaceInvitations"
        ) \
            .select("*") \
            .eq("token", token) \
            .eq("status", "pending") \
            .maybe_single() \
            .execute()

        if response is None:
            return None
        return response.data if response.data else None
    except Exception as e:
        logger.error(
            f"Error di _find_invitation_by_token (async): {e}",
            exc_info=True
        )
        return None


async def _delete_invitation_by_token(
    authed_client: AsyncClient,
    token: str
) -> bool:
    """
    Helper ASYNC: Menghapus undangan setelah diproses.
    """
    try:
        await authed_client.table("WorkspaceInvitations") \
            .delete() \
            .eq("token", token) \
            .execute()
        return True
    except Exception as e:
        logger.error(
            f"Error di _delete_invitation_by_token (async): {e}",
            exc_info=True
        )
        return False


async def respond_to_workspace_invitation(
    authed_client: AsyncClient,
    token: str,
    action: str,
    user: User
) -> Optional[Dict[str, Any]]:
    """
    (Async Native) Orkestrator Logika untuk menerima atau menolak undangan.

    Alur:
    1. Cari undangan berdasarkan token
    2. Validasi bahwa undangan untuk user yang benar
    3. Hapus undangan dari database
    4. Jika accept: tambahkan user ke workspace
    5. Jika reject: hanya kembalikan status rejected
    """
    # Import di sini untuk avoid circular dependency
    from .workspace_members import add_member_to_workspace

    invitation = await _find_invitation_by_token(authed_client, token)

    if not invitation:
        raise NotFoundError(
            "Undangan ini tidak valid atau telah kedaluwarsa."
        )

    invitee_email = invitation.get("invitee_email")
    invitee_user_id = invitation.get("invitee_user_id")

    if invitee_email and invitee_email.lower() != user.email.lower():
        raise DatabaseError(
            "invite_permission_denied",
            "Undangan ini ditujukan untuk alamat email yang berbeda."
        )
    if invitee_user_id and str(invitee_user_id) != str(user.id):
        raise DatabaseError(
            "invite_permission_denied",
            "Undangan ini ditujukan untuk pengguna yang berbeda."
        )

    workspace_id = invitation.get("workspace_id")
    role = invitation.get("role", "guest")

    await _delete_invitation_by_token(authed_client, token)

    if action == "reject":
        logger.info(
            f"Pengguna {user.id} menolak undangan ke workspace "
            f"{workspace_id}"
        )
        return {"status": "rejected"}

    if action == "accept":
        logger.info(
            f"Pengguna {user.id} menerima undangan ke workspace "
            f"{workspace_id} sebagai {role}"
        )

        # Panggil fungsi 'add_member_to_workspace'
        new_member_data = await add_member_to_workspace(
            authed_client=authed_client,
            workspace_id=UUID(workspace_id),
            user_id=user.id,
            role=MemberRole(role)
        )
        return new_member_data

    return None

