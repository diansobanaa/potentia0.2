from fastapi import APIRouter, Depends, HTTPException, status, Body 
from uuid import UUID
from typing import Union, Dict, Any
from app.models.user import User, UserUpdate 
from app.core.dependencies import (
    get_current_user, 
    get_current_user_and_client,
    UserServiceDep 
)
from app.services.user.user_service import UserService
from app.core.exceptions import DatabaseError, NotFoundError 
import logging # <-- Tambahkan

router = APIRouter(
    prefix="/auth",
    tags=["authentication"]
)
logger = logging.getLogger(__name__) 


@router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Endpoint untuk mendapatkan profil pengguna yang sedang login.
   
    """
    return current_user

# --- TAMBAHKAN ENDPOINT BARU DI BAWAH INI ---

@router.patch("/me", response_model=User)
async def update_users_me(
    payload: UserUpdate,
    user_service: UserServiceDep 
):
    """
    Memperbarui profil pengguna yang sedang login (nama, email, metadata).
    Keamanan: Pengguna hanya dapat memperbarui data mereka sendiri.
    """
    try:
        updated_user_data = await user_service.update_user_profile(payload)
        
        # Parse ulang data yang dikembalikan DB ke model Pydantic
        # untuk memastikan responsnya bersih dan tervalidasi.
        return User.model_validate(updated_user_data)

    except NotFoundError as e:
        logger.warning(f"Gagal update profil (404): {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Gagal update profil (500): {e}", exc_info=True)
        # Cek error spesifik untuk update email (jika duplikat)
        if "Unique constraint" in str(e) or "Users_email_key" in str(e):
             raise HTTPException(
                 status_code=status.HTTP_409_CONFLICT, 
                 detail="Email tersebut sudah digunakan."
             )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Error tidak terduga di update_users_me: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Terjadi kesalahan internal.")