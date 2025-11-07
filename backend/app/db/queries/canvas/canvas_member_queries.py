# File: backend/app/db/queries/canvas/canvas_member_queries.py

import logging
import asyncio
from uuid import UUID
from typing import List, Dict, Any, Optional
from supabase import Client
from postgrest import APIResponse
from postgrest.exceptions import APIError  # Untuk penanganan error RPC

# Impor exceptions kustom untuk error handling yang bersih
from app.core.exceptions import DatabaseError, NotFoundError
# Impor model Pydantic untuk validasi tipe data (role)
from app.models.canvas import CanvasRole
from app.models.user import User
from app.models.workspace import MemberRole

logger = logging.getLogger(__name__)

async def add_canvas_member(
    authed_client: Client,
    canvas_id: UUID,
    user_id: UUID,
    role: CanvasRole
) -> Dict[str, Any]:
    """
    Menambahkan (atau memperbarui) pengguna ke canvas spesifik.

    Fitur ini diekspos sebagai endpoint 'Invite' (POST /canvases/{id}/members).
    Logika ini menggunakan 'upsert':
    - Jika pengguna belum ada di 'CanvasAccess', ini akan menambahkan mereka.
    - Jika pengguna sudah ada, ini akan memperbarui 'role' mereka.
    
    Ini ditangani oleh 'on_conflict' pada constraint 'canvas_id, user_id'.
    """
    
    # Siapkan payload sesuai dengan skema database
    payload = {
        "canvas_id": str(canvas_id),
        "user_id": str(user_id),
        "role": role.value  # Ambil nilai string dari Enum, misal "editor"
    }
    
    def sync_db_call() -> Dict[str, Any]:
        """
        Membungkus panggilan database sinkron (blocking) agar bisa 
        dijalankan di thread terpisah oleh asyncio.to_thread.
        """
        try:
            # Jalankan 'upsert' (UPDATE atau INSERT)
            response: APIResponse = (
                authed_client.table("CanvasAccess")
                .upsert(
                    payload, 
                    on_conflict="canvas_id, user_id", # Kunci constraint
                    returning="representation"      # Minta data yang baru di-upsert
                )
                .execute()
            )
            
            # Fallback: Jika upsert berhasil tapi tidak ada data kembali
            if not response.data or len(response.data) == 0:
                logger.error(f"Gagal upsert anggota {user_id} ke {canvas_id} (data tidak dikembalikan).")
                raise DatabaseError("add_canvas_member_sync", "Gagal menambahkan anggota, tidak ada data dikembalikan.")
            
            # Kembalikan data anggota yang baru ditambahkan/diperbarui
            return response.data[0]
            
        except Exception as e:
            logger.error(f"Error saat add_canvas_member (sync) {user_id} ke {canvas_id}: {e}", exc_info=True)
            
            # Fallback cerdas: Tangani error jika 'user_id' yang diundang tidak ada
            if "foreign key constraint" in str(e) and "Users" in str(e):
                 raise NotFoundError(f"Pengguna dengan ID {user_id} tidak ditemukan.")
            
            # Lempar error umum jika bukan error FK
            raise DatabaseError("add_canvas_member_sync", str(e))

    try:
        # Jalankan fungsi 'sync_db_call' di thread terpisah
        data = await asyncio.to_thread(sync_db_call)
        return data
    except Exception as e:
        # Tangkap error yang dilempar dari 'sync_db_call'
        logger.error(f"Error di add_canvas_member (async): {e}", exc_info=True)
        # Lempar ulang error yang sudah kita kenali agar endpoint bisa menangani (404, 500)
        if isinstance(e, (DatabaseError, NotFoundError)):
            raise 
        raise DatabaseError("add_canvas_member_async", f"Error tidak terduka: {str(e)}")


async def list_canvas_members(
    authed_client: Client,
    canvas_id: UUID
) -> List[Dict[str, Any]]:
    """
    Mengambil daftar gabungan semua anggota yang memiliki akses ke canvas.

    Fitur ini diekspos sebagai endpoint 'List Members' (GET /canvases/{id}/members).
    
    Ini adalah implementasi 'Opsi 1' (Performa Tinggi) yang kita diskusikan:
    Logika penggabungan (Owner + Workspace + Invite) tidak dilakukan di Python,
    melainkan dieksekusi di dalam database menggunakan satu panggilan RPC
    'get_canvas_members_detailed'. Ini jauh lebih cepat dan efisien.
    """
    
    def sync_db_call() -> List[Dict[str, Any]]:
        """
        Membungkus panggilan RPC sinkron (blocking) agar bisa 
        dijalankan di thread terpisah.
        """
        try:
            # Tentukan nama fungsi RPC dan parameternya
            rpc_function = "get_canvas_members_detailed"
            params = {"p_canvas_id": str(canvas_id)}
            
            # Panggil RPC
            response: APIResponse = (
                authed_client.rpc(rpc_function, params)
                .execute()
            )
            
            # --- Fallback dan Penanganan Error ---
            
            # Fallback 1: Panggilan RPC gagal total
            if response is None:
                 logger.warning(f"RPC {rpc_function} mengembalikan None (canvas: {canvas_id})")
                 return []
                 
            # Fallback 2: RPC berhasil tapi tidak menemukan data
            if not response.data:
                # Ini adalah kasus yang valid (meskipun owner harusnya selalu ada)
                logger.info(f"RPC {rpc_function} tidak menemukan anggota untuk canvas: {canvas_id}")
                return []
                
            # --- Transformasi Data ---
            # RPC SQL mengembalikan: [{"role": "...", "user_details": {...}}]
            # Kita perlu mengubahnya menjadi: [{"role": "...", "user": {...}}]
            # agar sesuai dengan format yang diharapkan oleh frontend/API.
            
            formatted_list = []
            for item in response.data:
                formatted_list.append({
                    "role": item.get("role"),
                    "user": item.get("user_details") 
                })
            
            return formatted_list
            
        except APIError as e:
             # Fallback 3: RPC tidak ditemukan (error kritis)
             # Ini terjadi jika developer lupa menjalankan file SQL migrasi.
             if "PGRST202" in str(e.message): # 'Could not find the function'
                logger.critical(
                   f"FATAL: Fungsi RPC '{rpc_function}' "
                   f"tidak ditemukan di database Anda. Silakan jalankan SQL "
                   f"untuk membuat fungsi tersebut. Error: {e.message}"
                )
                raise DatabaseError("RPC_not_found", "Fungsi database untuk mengambil anggota tidak ditemukan.")
             
             # Error API Supabase lainnya
             logger.error(f"APIError saat list_canvas_members (sync) {canvas_id}: {e}", exc_info=True)
             raise DatabaseError("list_canvas_members_sync", str(e))
        except Exception as e:
            # Error Python umum
            logger.error(f"Error saat list_canvas_members (sync) {canvas_id}: {e}", exc_info=True)
            raise DatabaseError("list_canvas_members_sync", str(e))

    try:
        # Jalankan fungsi 'sync_db_call' di thread terpisah
        data = await asyncio.to_thread(sync_db_call)
        return data
    except Exception as e:
        # Tangkap error yang dilempar dari 'sync_db_call'
        logger.error(f"Error di list_canvas_members (async): {e}", exc_info=True)
        # Lempar ulang agar endpoint bisa menangani (500)
        if isinstance(e, DatabaseError):
            raise
        raise DatabaseError("list_canvas_members_async", f"Error tidak terduka: {str(e)}")