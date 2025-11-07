# File: backend/app/api/v1/endpoints/workspace_members.py

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from uuid import UUID

# --- [IMPOR MODEL DIPERBARUI] ---
from app.models.workspace import (
    WorkspaceMemberInviteOrAdd, # <- Kita gunakan model fleksibel ini
    WorkspaceMemberUpdate, 
    WorkspaceMemberResponse,
    MemberRole
)

# Impor dependencies keamanan
from app.core.dependencies import WorkspaceMemberDep, WorkspaceAdminAccessDep

# --- [IMPOR KUERI DIPERBARUI] ---
from app.db.queries.workspace.workspace_queries import (
    list_workspace_members,
    # 'add_member_to_workspace' TIDAK diimpor di sini
    create_workspace_invitation, # <- Hanya fungsi invite
    update_workspace_member_role,
    remove_workspace_member
)
# Impor exceptions
from app.core.exceptions import DatabaseError, NotFoundError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["workspaces"])


# --- [ENDPOINT 1: LIST MEMBERS (Tetap Sama)] ---
@router.get(
    "/", 
    response_model=List[WorkspaceMemberResponse],
    summary="List Workspace Members"
)
async def get_members_of_workspace(
    access_info: WorkspaceMemberDep # Keamanan: Cek apakah pengguna adalah anggota
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
        logger.error(f"Gagal list members (500) untuk workspace {workspace_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Error tidak terduga di get_members_of_workspace: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Terjadi kesalahan internal.")


# --- [ENDPOINT 2: "INVITE MEMBER" (Logika 'Invite-Only')] ---
@router.post(
    "/", 
    response_model=Dict[str, Any], # Mengembalikan data undangan
    status_code=status.HTTP_201_CREATED,
    summary="Invite Member to Workspace"
)
async def invite_member_to_workspace(
    payload: WorkspaceMemberInviteOrAdd, # <- Menggunakan model fleksibel
    access_info: WorkspaceAdminAccessDep # Keamanan: HANYA ADMIN
):
    """
    Mengirim undangan (invite) ke pengguna baru (via Email) atau
    pengguna yang sudah ada (via User ID).
    
    Fitur (Logika "Invite-Only"):
    Endpoint ini TIDAK menambahkan pengguna secara langsung.
    Ini membuat entri 'pending' di tabel 'WorkspaceInvitations'.
    Pengguna yang diundang harus menerima undangan ini.
    
    Keamanan:
    Hanya 'admin' workspace yang dapat mengirim undangan.
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
        
    except (DatabaseError, ValueError) as e:
        logger.warning(f"Gagal invite (4xx) ke workspace {workspace_id}: {e}", exc_info=True)
        # Jika error adalah 'invite_conflict' (dari kueri)
        if "invite_conflict" in str(e):
             raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, 
                detail=str(e) # Berikan pesan error spesifik
            )
        # Jika error adalah 'violates not-null constraint' (Fallback Bug 2)
        if "violates not-null constraint" in str(e):
             logger.error(f"FATAL: Gagal invite karena 'type' null. Pastikan DB dan Model sinkron. {e}")
             raise HTTPException(status_code=500, detail="Konfigurasi undangan error.")
             
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Error tidak terduga di invite_member_to_workspace: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Terjadi kesalahan internal.")
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
    access_info: WorkspaceAdminAccessDep # Keamanan: HANYA ADMIN
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
        logger.warning(f"Gagal update role (404) di workspace {workspace_id}: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DatabaseError as e:
        logger.warning(f"Gagal update role (4xx) di workspace {workspace_id}: {e}", exc_info=True)
        # Fallback: Jika mencoba me-demote owner
        if "owner_demote_prevented" in str(e):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Pemilik (Owner) workspace harus selalu menjadi Admin."
            )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Error tidak terduga di update_member_role: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Terjadi kesalahan internal.")

@router.delete(
    "/{user_id_to_remove}", 
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove Member"
)
async def remove_member_from_workspace(
    user_id_to_remove: UUID,
    access_info: WorkspaceAdminAccessDep # Keamanan: HANYA ADMIN
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
        logger.warning(f"Gagal remove (404) di workspace {workspace_id}: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DatabaseError as e:
        logger.warning(f"Gagal remove (4xx) di workspace {workspace_id}: {e}", exc_info=True)
        # Fallback: Jika mencoba menghapus owner
        if "owner_remove_prevented" in str(e):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Pemilik (Owner) workspace tidak dapat dihapus."
            )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Error tidak terduga di remove_member_from_workspace: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Terjadi kesalahan internal.")