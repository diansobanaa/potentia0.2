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
import httpx
from app.core.config import settings

router = APIRouter(
    prefix="/auth",
    tags=["authentication"]
)
logger = logging.getLogger(__name__) 


@router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Mengambil data profil lengkap (User model) untuk pengguna yang saat ini terotentikasi.
    
    INPUT: None (Otentikasi melalui header JWT).
    OUTPUT: User (ID, email, nama, subscription_tier).
    
    KAPAN DIGUNAKAN: Dipanggil saat inisialisasi aplikasi atau setelah login/refresh sesi untuk memverifikasi keaktifan sesi dan memuat detail pengguna ke UI.
    """
    return current_user

# --- TAMBAHKAN ENDPOINT BARU DI BAWAH INI ---

@router.patch("/me", response_model=User)
async def update_users_me(
    payload: UserUpdate,
    user_service: UserServiceDep 
):
    """
    Memperbarui atribut tertentu dari profil pengguna yang sedang login (nama, email, metadata).
    
    INPUT: UserUpdate (Opsional: name, email, metadata: {phone_number: str}).
    OUTPUT: User (Objek pengguna yang telah diperbarui).
    
    KAPAN DIGUNAKAN: Di halaman 'Settings' pengguna saat memperbarui informasi profil. Memerlukan sinkronisasi antara tabel 'auth.users' dan 'public.Users'.
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

@router.post(
    "/refresh",
    response_model=Dict[str, str],
    summary="Refresh JWT access token"
)
async def refresh_access_token(
    refresh_token: str = Body(..., embed=True)
):
    """
    Refresh JWT access token using a valid refresh token.
    
    This endpoint exchanges a valid refresh token for a new JWT access token.
    The refresh token must be valid and not expired.
    """
    try:
        # Use Supabase auth endpoint to refresh token
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=refresh_token",
                headers={
                    "apikey": settings.SUPABASE_ANON_KEY,
                    "Content-Type": "application/json"
                },
                json={"refresh_token": refresh_token}
            )
            
            if response.status_code != 200:
                logger.warning(f"Token refresh failed: {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired refresh token"
                )
            
            token_data = response.json()
            
            return {
                "access_token": token_data.get("access_token"),
                "token_type": "bearer",
                "expires_in": token_data.get("expires_in"),
                "refresh_token": token_data.get("refresh_token")
            }
            
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error during token refresh: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to refresh token"
        )
    except HTTPException as e:
        # Re-raise HTTPException to preserve the intended status code
        raise e
    except Exception as e:
        logger.error(f"Unexpected error during token refresh: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )