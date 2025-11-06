import logging
import asyncio
from typing import Dict, Any, Optional
from supabase import Client
from app.models.user import User, UserUpdate
from app.core.exceptions import DatabaseError, NotFoundError
from app.db.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

class UserService:
    """
    Menangani logika bisnis untuk memperbarui data pengguna.
    """
    def __init__(self, authed_client: Client, user: User):
        self.client = authed_client
        self.user = user
        self.admin_client = get_supabase_client()

    async def update_user_profile(self, update_data: UserUpdate) -> Dict[str, Any]:
        """
        Memperbarui profil pengguna di `auth.users` (via Admin API)
        DAN `public."Users"` (via RLS client).
        """
        # --- 1. Siapkan Payload ---
        auth_kwargs: Dict[str, Any] = {}
        public_payload: Dict[str, Any] = {}

        if update_data.email and update_data.email != self.user.email:
            auth_kwargs["email"] = update_data.email

        if update_data.name:
            public_payload["name"] = update_data.name
            auth_kwargs.setdefault("user_metadata", {})["display_name"] = update_data.name

        if update_data.metadata and update_data.metadata.phone_number:
            phone = update_data.metadata.phone_number.strip()
            if phone.startswith("0"):
                phone = "+62" + phone[1:]
            elif not phone.startswith("+"):
                phone = "+62" + phone
            public_payload["user_metadata"] = {"phone_number": phone}
            auth_kwargs.setdefault("user_metadata", {})["phone_number"] = phone

        # --- 2. Jalankan Sinkronisasi ---
        def sync_db_calls():
            try:
                user_id_str = str(self.user.id)

                # A. Update ke auth.users (Admin)
                if auth_kwargs:
                    logger.info(f"Memperbarui 'auth.users' (via Admin) untuk user {user_id_str}...")

                    # Bungkus semua atribut dalam 'attributes' sesuai format baru SDK
                    self.admin_client.auth.admin.update_user_by_id(
                        user_id_str,
                        attributes=auth_kwargs  # <--- perbaikan utama
                    )

                # B. Update ke public.Users (RLS)
                if public_payload:
                    logger.info(f"Memperbarui 'public.Users' (via RLS) untuk user {user_id_str}...")
                    response = (
                        self.client.table("Users")
                        .update(public_payload)
                        .eq("user_id", user_id_str)
                        .execute()
                    )
                    if not response.data:
                        raise NotFoundError("Gagal memperbarui profil di public.Users.")

                # C. Ambil Data Terbaru
                response = (
                    self.client.table("Users")
                    .select("*")
                    .eq("user_id", user_id_str)
                    .single()
                    .execute()
                )
                if not response.data:
                    raise NotFoundError("Profil pengguna tidak ditemukan setelah update.")
                return response.data

            except Exception as e:
                logger.error(f"Error saat update profil (sync) untuk {self.user.id}: {e}", exc_info=True)
                raise DatabaseError("update_profile_sync", str(e))

        # --- 3. Jalankan di Thread Terpisah ---
        try:
            updated_user_data = await asyncio.to_thread(sync_db_calls)
            logger.info(f"Profil untuk user {self.user.id} berhasil diperbarui.")
            return updated_user_data

        except Exception as e:
            logger.error(f"Error di update_user_profile (async): {e}", exc_info=True)
            if isinstance(e, (DatabaseError, NotFoundError)):
                raise
            raise DatabaseError("update_profile_async", str(e))
