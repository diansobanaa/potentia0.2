from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from uuid import UUID
from typing import Union
from supabase import Client # <-- Impor Client utama
from app.core.config import settings
from app.db.supabase_client import get_supabase_client
from app.models.user import User, SubscriptionTier

security = HTTPBearer(auto_error=False)

# Klien anonim dasar, hanya untuk membuat klien yang diautentikasi
supabase_anon_client = get_supabase_client()

class GuestUser:
    id: Union[UUID, None] = None
    is_guest: bool = True
    subscription_tier: SubscriptionTier = SubscriptionTier.user
    
    def __init__(self):
        # Beri klien anonim untuk operasi tamu
        self.client = supabase_anon_client

async def get_current_user_and_client( # <-- NAMA FUNGSI SUDAH DIPERBAIKI
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Dependency inti baru.
    Memvalidasi token, membuat klien Supabase yang diautentikasi,
    dan mengambil profil pengguna internal.
    Mengembalikan dict berisi {"user": User, "client": Client}
    """
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    token = credentials.credentials
    
    try:
        # 1. Buat klien Supabase BARU yang spesifik untuk permintaan ini
        # Klien ini "login" sebagai pengguna yang mengirim permintaan
        authed_client = Client(
            supabase_url=settings.SUPABASE_URL,
            supabase_key=settings.SUPABASE_ANON_KEY
        )
        # Atur sesi klien ini menggunakan token pengguna
        authed_client.auth.set_session(access_token=token, refresh_token=token)

        # 2. Ambil data pengguna dari Supabase (memvalidasi token)
        user_response = authed_client.auth.get_user(token)
        
        if user_response.user is None:
             raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token or user not found in Supabase")

        user_id = user_response.user.id

        # 3. Cari profil di tabel *internal* "Users" menggunakan klien yang sudah diautentikasi
        # Ini sekarang akan mematuhi RLS Anda dengan benar
        profile_response = authed_client.table("Users").select("*").eq("user_id", user_id).single().execute()
        
        if not profile_response.data:
            raise HTTPException(status_code=404, detail="User profile not found in internal database.")
            
        # 4. Buat model User
        profile_data = profile_response.data
        user_model = User(
            id=profile_data["user_id"], 
            email=profile_data["email"], 
            name=profile_data.get("name"),
            subscription_tier=profile_data.get("subscription_tier", SubscriptionTier.user)
        )
        
        # 5. Kembalikan dict dengan user DAN kliennya
        return {"user": user_model, "client": authed_client}
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Could not validate credentials: {str(e)}")

async def get_current_user(auth_info: dict = Depends(get_current_user_and_client)) -> User: # <-- Diperbarui
    """
    Dependency yang diupdate: Hanya mengembalikan model User.
    Semua dependency lama Anda yang menggunakan get_current_user akan tetap berfungsi.
    """
    return auth_info["user"]

async def get_current_user_or_guest(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Dependency yang diupdate: Mengembalikan user (atau GuestUser) DAN klien (autentikasi atau anonim).
    """
    if credentials:
        try:
            # Jika ada token, coba dapatkan user dan klien yang diautentikasi
            return await get_current_user_and_client(credentials) # <-- Diperbarui
        except HTTPException:
            # Jika token gagal, perlakukan sebagai tamu
            return {"user": GuestUser(), "client": supabase_anon_client}
    else:
        # Jika tidak ada token, perlakukan sebagai tamu
        return {"user": GuestUser(), "client": supabase_anon_client}

async def get_user_tier(current_user: User = Depends(get_current_user)) -> SubscriptionTier:
    """Fungsi ini tetap bekerja tanpa perubahan."""
    return current_user.subscription_tier

async def require_pro_user(tier: SubscriptionTier = Depends(get_user_tier)):
    """Fungsi ini tetap bekerja tanpa perubahan."""
    if tier not in [SubscriptionTier.pro, SubscriptionTier.admin]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This feature requires a Pro subscription."
        )
    return tier

async def require_admin_user(current_user: User = Depends(get_current_user)):
    """Fungsi ini tetap bekerja tanpa perubahan."""
    if current_user.subscription_tier != SubscriptionTier.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required."
        )
    return current_user

async def get_current_workspace_member(
    workspace_id: UUID,
    auth_info: dict = Depends(get_current_user_and_client) # Diubah ke dependency baru
):
    from app.db.queries.workspace_queries import check_user_membership
    
    current_user = auth_info["user"]
    authed_client = auth_info["client"] # Ambil klien yang diautjugaentikasi
    
    # Teruskan kliennya ke fungsi query
    membership = check_user_membership(authed_client, workspace_id, current_user.id)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this workspace."
        )
    
    # Kembalikan dict lengkap
    return {"membership": membership, "user": current_user, "client": authed_client}

async def get_canvas_access(
    canvas_id: UUID, 
    auth_info: dict = Depends(get_current_user_or_guest) # Diubah ke dependency baru
):
    current_user = auth_info["user"]
    authed_client = auth_info["client"] # Ambil klien (bisa anonim atau autentikasi)
    
    if isinstance(current_user, GuestUser):
        raise HTTPException(status_code=401, detail="Authentication required to access canvas.")
    
    from app.db.queries.canvas_queries import get_canvas_by_id
    from app.db.queries.workspace_queries import check_user_membership

    # Gunakan authed_client untuk query
    canvas = get_canvas_by_id(authed_client, canvas_id)
    if not canvas:
        raise HTTPException(status_code=404, detail="Canvas not found.")
    
    if canvas.get("user_id") and str(canvas["user_id"]) == str(current_user.id):
        # Kembalikan dict lengkap
        return {"canvas": canvas, "user": current_user, "client": authed_client}
    
    if canvas.get("workspace_id"):
        # Gunakan authed_client untuk query
        membership = check_user_membership(authed_client, UUID(canvas["workspace_id"]), current_user.id)
        if membership:
            # Kembalikan dict lengkap
            return {"canvas": canvas, "user": current_user, "client": authed_client}
            
    raise HTTPException(status_code=403, detail="Access denied to this canvas.")

