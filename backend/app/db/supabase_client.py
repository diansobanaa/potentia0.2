# backend/app/db/supabase_client.py
# (Diperbarui dengan 'async def' dan 'await')

from supabase.client import AsyncClient, create_async_client
from app.core.config import settings

_supabase_admin_client: AsyncClient | None = None

# --- PERBAIKAN: Fungsi ini sekarang 'async' ---
async def get_supabase_admin_async_client() -> AsyncClient:
    """
    (Async Native) Mengembalikan instance AsyncClient singleton untuk 
    koneksi admin (service_role).
    """
    global _supabase_admin_client
    if _supabase_admin_client is None:
        # --- PERBAIKAN: 'await' pembuatannya ---
        _supabase_admin_client = await create_async_client(
            settings.SUPABASE_URL, 
            settings.SUPABASE_SERVICE_ROLE_KEY
        )
    return _supabase_admin_client