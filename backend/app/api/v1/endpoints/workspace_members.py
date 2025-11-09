# File: backend/app/api/v1/endpoints/workspace_members.py

import logging
from fastapi import APIRouter, HTTPException, status
from typing import List, Dict, Any
from uuid import UUID

# --- [IMPOR MODEL DIPERBARUI] ---
from app.models.workspace import (
    WorkspaceMemberInviteOrAdd,  # <- Kita gunakan model fleksibel ini
    WorkspaceMemberUpdate,
    WorkspaceMemberResponse,
)

# Impor dependencies keamanan
from app.core.dependencies import WorkspaceMemberDep, WorkspaceAdminAccessDep

# --- [IMPOR KUERI DIPERBARUI] ---
from app.db.queries.workspace.workspace_queries import (
    list_workspace_members,
    # 'add_member_to_workspace' TIDAK diimpor di sini
    create_workspace_invitation,  # <- Hanya fungsi invite
    update_workspace_member_role,
    remove_workspace_member
)
# Impor exceptions
from app.core.exceptions import DatabaseError, NotFoundError
# --- [BARU] Impor rate limiter untuk proteksi email ---
from app.services.redis_rate_limiter import rate_limiter

logger = logging.getLogger(__name__)

router = APIRouter(tags=["workspaces"])


# --- [ENDPOINT 1: LIST MEMBERS (Tetap Sama)] ---
@router.get(
    "/",
    response_model=List[WorkspaceMemberResponse],
    summary="List Workspace Members"
)
async def get_members_of_workspace(
    # Keamanan: Cek apakah pengguna adalah anggota
    access_info: WorkspaceMemberDep
):
    """
    Mengambil daftar semua anggota yang terdaftar di 'WorkspaceMembers'.

    Keamanan:
    Hanya anggota yang sudah ada di workspace yang dapat melihat
    daftar anggota lainnya.
    """
    workspace_id = access_info["membership"]["workspace_id"]
    authed_client = access_info["client"]

    try:
        members_data = await list_workspace_members(
            authed_client=authed_client,
            workspace_id=workspace_id
        )

        # Transformasi data mentah ke model respons Pydantic
        response_list = [
            WorkspaceMemberResponse(role=item['role'], user=item['user'])
            for item in members_data if item.get('user')
        ]
        return response_list

    except DatabaseError as e:
        logger.error(
            f"Gagal list members (500) untuk workspace {workspace_id}: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            f"Error tidak terduga di get_members_of_workspace: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Terjadi kesalahan internal."
        )


# --- [ENDPOINT 2: "INVITE MEMBER" (Logika 'Invite-Only')] ---
@router.post(
    "/",
    response_model=Dict[str, Any],  # Mengembalikan data undangan
    status_code=status.HTTP_201_CREATED,
    summary="Invite Member to Workspace"
)
async def invite_member_to_workspace(
    payload: WorkspaceMemberInviteOrAdd,  # <- Menggunakan model fleksibel
    access_info: WorkspaceAdminAccessDep  # Keamanan: HANYA ADMIN
):
    """
    Mengirim undangan (invite) ke pengguna baru (via Email) atau
    pengguna yang sudah ada (via User ID).

    Fitur (Logika "Invite-Only"):
    Endpoint ini TIDAK menambahkan pengguna secara langsung.
    Ini membuat entri 'pending' di tabel 'WorkspaceInvitations'.
    Pengguna yang diundang harus menerima undangan ini.

    Keamanan:
    - Hanya 'admin' workspace yang dapat mengirim undangan.
    - Rate limiting per user (admin): 50 undangan per jam
    - Rate limiting per workspace: 100 undangan per jam
    - Rate limiting per email: 5 undangan per jam
      (mencegah spam/harassment)
    """
    workspace_id = access_info["membership"]["workspace_id"]
    authed_client = access_info["client"]
    admin_user = access_info["user"]

    # --- Fallback: Mencegah admin mengundang diri sendiri ---
    if (payload.user_id and payload.user_id == admin_user.id) or \
       (payload.email and payload.email == admin_user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tidak dapat mengundang diri sendiri."
        )

    # --- [BARU] Rate Limiting: Proteksi terhadap spam email ---
    # Wrapped dalam try-except untuk fallback jika rate limiter error
    try:
        # 1. Cek batas undangan per user (admin)
        user_allowed = await rate_limiter.check_invite_limit_per_user(
            user_id=admin_user.id,
            limit=50,  # 50 undangan per jam per admin
            window_seconds=3600
        )
        if not user_allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    "Terlalu banyak undangan yang dikirim. "
                    "Silakan coba lagi nanti (batas: 50 undangan per jam)."
                )
            )

        # 2. Cek batas undangan per workspace
        workspace_allowed = (
            await rate_limiter.check_invite_limit_per_workspace(
                workspace_id=workspace_id,
                limit=100,  # 100 undangan/jam per workspace
                window_seconds=3600
            )
        )
        if not workspace_allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    "Workspace ini telah mencapai batas undangan. "
                    "Silakan coba lagi nanti (batas: 100 undangan per jam)."
                )
            )

        # 3. Cek batas undangan per email (jika invite via email)
        if payload.email:
            email_allowed = await rate_limiter.check_invite_limit_per_email(
                email=payload.email,
                limit=5,  # 5 undangan per jam per email
                window_seconds=3600
            )
            if not email_allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=(
                        "Email ini telah menerima terlalu banyak undangan. "
                        "Silakan coba lagi nanti "
                        "(batas: 5 undangan per jam per email)."
                    )
                )
    except HTTPException:
        # Re-raise HTTPException (rate limit exceeded)
        raise
    except Exception as e:
        # Fallback: Jika rate limiter error, log dan lanjutkan
        # (tidak crash aplikasi)
        logger.warning(
            f"Error saat check rate limit untuk invite: {e}. "
            "Melanjutkan tanpa rate limit check.",
            exc_info=True
        )
        # Lanjutkan proses invite tanpa rate limiting
    # --- [AKHIR Rate Limiting] ---

    try:
        # --- [LOGIKA BARU] ---
        # Panggil fungsi 'create_workspace_invitation' yang sudah 'pintar'
        # Kita teruskan 'email' dan 'user_id', salah satunya akan None,
        # dan fungsi kueri akan menanganinya.
        new_invitation = await create_workspace_invitation(
            authed_client=authed_client,
            workspace_id=workspace_id,
            inviter_id=admin_user.id,
            role=payload.role,
            invitee_email=payload.email,
            invitee_user_id=payload.user_id
        )
        # --- [AKHIR LOGIKA BARU] ---

        # TODO: Tambahkan trigger email di sini nanti
        # (misal: background_tasks.add_task(send_invite_email, ...))

        return new_invitation

    except DatabaseError as e:
        # Handle DatabaseError dengan pesan yang lebih jelas
        error_message = str(e)
        logger.warning(
            f"Gagal invite (DatabaseError) ke workspace {workspace_id}: {e}",
            exc_info=True
        )

        # Jika error adalah 'invite_conflict' (dari kueri)
        if "invite_conflict" in error_message:
            # Extract pesan error yang lebih user-friendly
            if "sudah menjadi anggota" in error_message:
                detail_msg = (
                    "Pengguna ini sudah menjadi anggota workspace."
                )
            elif "sudah memiliki undangan" in error_message:
                detail_msg = (
                    "Pengguna ini sudah memiliki undangan yang tertunda."
                )
            else:
                detail_msg = error_message

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=detail_msg
            )

        # Jika error adalah database constraint violation
        if ("violates" in error_message.lower() or
                "constraint" in error_message.lower()):
            logger.error(
                f"Database constraint error saat invite: {error_message}",
                exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Data undangan tidak valid. Silakan periksa kembali."
            )

        # Error database lainnya
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gagal membuat undangan. Silakan coba lagi nanti."
        )

    except ValueError as e:
        # Handle ValueError (misal: user_id atau email tidak valid)
        error_message = str(e)
        logger.warning(
            f"Gagal invite (ValueError) ke workspace {workspace_id}: {e}",
            exc_info=True
        )
        detail_msg = (
            error_message if error_message
            else "Data undangan tidak valid."
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail_msg
        )

    except Exception as e:
        # Handle semua error lainnya
        error_message = str(e)
        logger.error(
            f"Error tidak terduga di invite_member_to_workspace: {e}",
            exc_info=True
        )

        # Cek apakah ini APIError dari Supabase
        if "APIError" in str(type(e)) or "postgrest" in error_message.lower():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Gagal terhubung ke database. Silakan coba lagi nanti."
            )

        # Error umum lainnya
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Terjadi kesalahan internal. Silakan coba lagi nanti."
        )
# --- [AKHIR PERUBAHAN ENDPOINT POST] ---


# --- [ENDPOINT 3 & 4: (Tetap Sama)] ---
@router.patch(
    "/{user_id_to_update}",
    response_model=Dict[str, Any],
    summary="Update Member Role"
)
async def update_member_role(
    user_id_to_update: UUID,
    payload: WorkspaceMemberUpdate,
    access_info: WorkspaceAdminAccessDep  # Keamanan: HANYA ADMIN
):
    """
    Memperbarui role dari anggota yang SUDAH ADA di 'WorkspaceMembers'.

    Keamanan:
    Hanya 'admin' yang bisa mengubah role.
    Fallback: Mencegah 'owner' diturunkan rolenya.
    """
    workspace_id = access_info["membership"]["workspace_id"]
    authed_client = access_info["client"]

    try:
        updated_member = await update_workspace_member_role(
            authed_client=authed_client,
            workspace_id=workspace_id,
            user_id_to_update=user_id_to_update,
            new_role=payload.role
        )
        return updated_member

    except NotFoundError as e:
        logger.warning(
            f"Gagal update role (404) di workspace {workspace_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except DatabaseError as e:
        logger.warning(
            f"Gagal update role (4xx) di workspace {workspace_id}: {e}",
            exc_info=True
        )
        # Fallback: Jika mencoba me-demote owner
        if "owner_demote_prevented" in str(e):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Pemilik (Owner) workspace harus selalu menjadi Admin."
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            f"Error tidak terduga di update_member_role: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Terjadi kesalahan internal."
        )


@router.delete(
    "/{user_id_to_remove}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove Member"
)
async def remove_member_from_workspace(
    user_id_to_remove: UUID,
    access_info: WorkspaceAdminAccessDep  # Keamanan: HANYA ADMIN
):
    """
    Mengeluarkan (remove) anggota dari 'WorkspaceMembers'.

    Keamanan:
    Hanya 'admin' yang bisa mengeluarkan anggota.
    Fallback: Mencegah 'owner' mengeluarkan dirinya sendiri.
    """
    workspace_id = access_info["membership"]["workspace_id"]
    authed_client = access_info["client"]

    try:
        await remove_workspace_member(
            authed_client=authed_client,
            workspace_id=workspace_id,
            user_id_to_remove=user_id_to_remove
        )
        # Sukses, kembalikan 204 No Content
        return

    except NotFoundError as e:
        logger.warning(
            f"Gagal remove (404) di workspace {workspace_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except DatabaseError as e:
        logger.warning(
            f"Gagal remove (4xx) di workspace {workspace_id}: {e}",
            exc_info=True
        )
        # Fallback: Jika mencoba menghapus owner
        if "owner_remove_prevented" in str(e):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Pemilik (Owner) workspace tidak dapat dihapus."
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            f"Error tidak terduga di remove_member_from_workspace: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Terjadi kesalahan internal."
        )
