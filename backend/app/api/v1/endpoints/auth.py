from fastapi import APIRouter, Depends, HTTPException, status, Body 
from uuid import UUID
from typing import Union, Dict, Any # Tambahkan Dict, Any
from app.models.user import User
# Dependensi
from app.core.dependencies import get_current_user, get_current_user_and_client 


router = APIRouter(
    prefix="/auth",
    tags=["authentication"]
)

@router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Endpoint untuk mendapatkan profil pengguna yang sedang login.
    Menggunakan dependency get_current_user.
    """
    return current_user

