# File: backend/app/api/v1/endpoints/invitations.py
# (File Baru)

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any
from uuid import UUID

# Impor model Pydantic yang kita buat
from app.models.workspace import WorkspaceInvitationRespond
from app.models.user import User

# Impor dependency keamanan (hanya perlu user yang login)
from app.core.dependencies import AuthInfoDep

# Impor fungsi query yang baru kita buat
from app.db.queries.workspace.workspace_queries import respond_to_workspace_invitation
# Impor exceptions
from app.core.exceptions import DatabaseError, NotFoundError

logger = logging.getLogger(__name__)

# Definisikan router baru
router = APIRouter(
    prefix="/invitations",
    tags=["invitations"]
)

@router.post(
    "/workspace/respond", 
    response_model=Dict[str, Any],
    summary="Respond to Workspace Invitation"
)
async def respond_to_workspace_invite(
    payload: WorkspaceInvitationRespond,
    auth_info: AuthInfoDep # Keamanan: Pengguna HARUS login
):
    """
    Endpoint untuk pengguna yang login menerima (accept) 
    atau menolak (reject) undangan workspace.
    
    Alur:
    1. Pengguna menerima email/notifikasi.
    2. Pengguna login ke aplikasi.
    3. Frontend mengirim 'token' dan 'action' ke endpoint ini.
    INPUT: WorkspaceInvitationRespond (token: str, action: InvitationAction ['accept'/'reject']).
    OUTPUT: Dict[str, Any] (Data anggota baru jika diterima, atau {"status": "rejected"}).
    
    KAPAN DIGUNAKAN: Dipanggil oleh klien (setelah pengguna mengklik link di email dan login) untuk memproses token undangan.
    """
    user = auth_info["user"]
    client = auth_info["client"]

    try:
        # Memanggil logika inti di 'workspace_queries'
        result = await respond_to_workspace_invitation(
            authed_client=client,
            token=payload.token,
            action=payload.action.value, # "accept" or "reject"
            user=user
        )
        
        # Fallback jika logika tidak mengembalikan hasil
        if not result:
             raise HTTPException(status_code=500, detail="Gagal memproses undangan.")
             
        # Jika berhasil 'accept', result berisi data member baru
        # Jika berhasil 'reject', result berisi {"status": "rejected"}
        return result

    except NotFoundError as e:
        # Fallback: Token tidak valid atau kedaluwarsa
        logger.warning(f"Gagal merespons undangan (404): {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DatabaseError as e:
        # Fallback: Error logika (misal: email tidak cocok, invite conflict)
        logger.warning(f"Gagal merespons undangan (4xx): {e}", exc_info=True)
        if "invite_permission_denied" in str(e):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail=str(e)
            )
        # Tangani error 'invite_conflict' jika terjadi di 'add_member'
        if "invite_conflict" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e)
            )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error tidak terduga di respond_to_workspace_invite: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Terjadi kesalahan internal.")