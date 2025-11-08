# backend/app/services/user/user_service.py
# (Diperbarui untuk AsyncClient ganda)

import logging
import asyncio
from typing import Dict, Any, Optional
# --- PERBAIKAN: Impor AsyncClient ---
from supabase.client import AsyncClient
from app.models.user import User, UserUpdate
from app.core.exceptions import DatabaseError, NotFoundError
# (Kita tidak lagi membutuhkan get_supabase_client di sini)

logger = logging.getLogger(__name__)

class UserService:
    """
    Menangani logika bisnis untuk memperbarui data pengguna.
    """
    def __init__(
        self, 
        authed_client: AsyncClient, # <-- Tipe diubah 
        user: User,
        admin_client: AsyncClient  # <-- Dependensi baru
    ):
        self.client = authed_client
        self.user = user
        self.admin_client = admin_client # Klien Admin Service Role

    async def _async_db_calls(
        self, 
        auth_kwargs: Dict[str, Any], 
        public_payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        [FUNGSI BARU] Menjalankan panggilan DB secara asinkron.
        Menggantikan 'sync_db_calls'.
        """
        try:
            user_id_str = str(self.user.id)

            # A. Update ke auth.users (Admin)
            if auth_kwargs:
                logger.info(f"Memperbarui 'auth.users' (via Admin Async) untuk user {user_id_str}...")
                
                await self.admin_client.auth.admin.update_user_by_id(
                    user_id_str,
                    attributes=auth_kwargs
                ) # <-- 'await'

            # B. Update ke public.Users (RLS)
            if public_payload:
                logger.info(f"Memperbarui 'public.Users' (via RLS Async) untuk user {user_id_str}...")
                response = await self.client.table("Users") \
                    .update(public_payload) \
                    .eq("user_id", user_id_str) \
                    .execute() # <-- 'await'
                if not response.data:
                    raise NotFoundError("Gagal memperbarui profil di public.Users.")

            # C. Ambil Data Terbaru
            response = await self.client.table("Users") \
                .select("*") \
                .eq("user_id", user_id_str) \
                .single() \
                .execute() # <-- 'await'
            
            if not response.data:
                raise NotFoundError("Profil pengguna tidak ditemukan setelah update.")
            return response.data

        except Exception as e:
            logger.error(f"Error saat update profil (async native) untuk {self.user.id}: {e}", exc_info=True)
            raise DatabaseError("update_profile_async", str(e))

    async def update_user_profile(self, update_data: UserUpdate) -> Dict[str, Any]:
        """
        Memperbarui profil pengguna di `auth.users` (via Admin API)
        DAN `public."Users"` (via RLS client).
        """
        # --- 1. Siapkan Payload (Logika tidak berubah) ---
        auth_kwargs: Dict[str, Any] = {}
        public_payload: Dict[str, Any] = {}

        if update_data.email and update_data.email != self.user.email:
            auth_kwargs["email"] = update_data.email
        if update_data.name:
            public_payload["name"] = update_data.name
            auth_kwargs.setdefault("user_metadata", {})["display_name"] = update_data.name
        if update_data.metadata and update_data.metadata.phone_number:
            phone = update_data.metadata.phone_number.strip()
            if phone.startswith("0"): phone = "+62" + phone[1:]
            elif not phone.startswith("+"): phone = "+62" + phone
            public_payload["user_metadata"] = {"phone_number": phone}
            auth_kwargs.setdefault("user_metadata", {})["phone_number"] = phone

        # --- 2. Jalankan Panggilan Async (Refactored) ---
        try:
            # --- PERBAIKAN: Hapus 'asyncio.to_thread' ---
            updated_user_data = await self._async_db_calls(auth_kwargs, public_payload)
            logger.info(f"Profil untuk user {self.user.id} berhasil diperbarui.")
            return updated_user_data

        except Exception as e:
            logger.error(f"Error di update_user_profile (orchestrator): {e}", exc_info=True)
            if isinstance(e, (DatabaseError, NotFoundError)):
                raise
            raise DatabaseError("update_profile_orchestrator", str(e))