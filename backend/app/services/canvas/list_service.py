# File: backend/services/canvas/list_service.py
# (FILE DIPINDAHKAN & DIREFACTOR - Asal: app/services/canvas_list_service.py)

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID

# Impor dependensi service dan model
from app.models.user import User
from app.models.canvas import CanvasCreate, CanvasUpdate #
from app.core.exceptions import DatabaseError, NotFoundError, PermissionError

# Impor file query DB yang baru
from app.db.queries.canvas import canvas_queries
from app.db.supabase_client import get_supabase_admin_async_client

logger = logging.getLogger(__name__)

class CanvasListService:
    """
    Service untuk mengelola operasi CRUD pada canvas.
    Mendelegasikan panggilan DB ke 'canvas_queries'.
    """
    
    def __init__(self, auth_info: Dict[str, Any]):
        self.user: User = auth_info["user"]
        self.client = auth_info["client"] # Client ber-auth user
        self.admin_client = None
    
    async def _get_admin_client(self):
        """Get admin client jika belum ada."""
        if self.admin_client is None:
            self.admin_client = await get_supabase_admin_async_client()
        return self.admin_client
    
    async def create_new_canvas(
        self, 
        canvas_data: CanvasCreate
    ) -> Dict[str, Any]:
        """
        Membuat canvas pribadi atau workspace.
        """
        admin_client = await self._get_admin_client()
        
        # --- Logika Bisnis ---
        # Jika workspace_id disediakan, validasi apakah user adalah anggota
        if canvas_data.workspace_id:
            try:
                # Cek keanggotaan (menggunakan client user, bukan admin)
                ws_member_resp = await self.client.table("workspace_members") \
                    .select("role") \
                    .eq("workspace_id", str(canvas_data.workspace_id)) \
                    .eq("user_id", str(self.user.id)) \
                    .maybe_single() \
                    .execute()
                
                if not ws_member_resp.data:
                    raise PermissionError("Gagal membuat canvas: Anda bukan anggota workspace tersebut.")
            except Exception as e:
                logger.warning(f"Gagal validasi keanggotaan workspace: {e}")
                raise PermissionError(f"Gagal memvalidasi keanggotaan workspace: {e}")

        # Panggil fungsi query DB
        try:
            new_canvas = await canvas_queries.create_canvas_db(
                admin_client=admin_client,
                canvas_data=canvas_data,
                creator_id=self.user.id
            )
            return new_canvas
        except DatabaseError as e:
            logger.error(f"Gagal membuat canvas di service: {e}", exc_info=True)
            raise # Lemparkan ulang error
            
    async def get_user_canvases(
        self, 
        limit: int = 20, 
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Mendapatkan daftar canvas yang dapat diakses oleh pengguna.
        """
        admin_client = await self._get_admin_client()
        
        try:
            canvases = await canvas_queries.get_user_canvases_db(
                admin_client=admin_client,
                user_id=self.user.id,
                limit=limit,
                offset=offset
            )
            return canvases
        except DatabaseError as e:
            logger.error(f"Gagal mengambil canvas di service: {e}", exc_info=True)
            raise

    async def update_canvas(
        self, 
        canvas_id: UUID, 
        canvas_data: CanvasUpdate
    ) -> Dict[str, Any]:
        """
        Memperbarui detail canvas.
        (Akses di-handle oleh dependency di endpoint)
        """
        admin_client = await self._get_admin_client()
        
        # --- Logika Bisnis ---
        # Membangun payload update dari model Pydantic
        # Gunakan 'exclude_unset=True' agar field None tidak ikut
        update_data = canvas_data.model_dump(exclude_unset=True)
        
        # Cek jika tidak ada data untuk diupdate
        if not update_data:
            raise ValueError("Tidak ada field valid untuk diupdate.")
            
        try:
            updated_canvas = await canvas_queries.update_canvas_db(
                admin_client=admin_client,
                canvas_id=canvas_id,
                update_data=update_data
            )
            return updated_canvas
            
        except (NotFoundError, DatabaseError, ValueError) as e:
            logger.warning(f"Gagal update canvas {canvas_id}: {e}")
            raise
    
    async def delete_canvas(self, canvas_id: UUID):
        """
        Menghapus canvas.
        (Akses di-handle oleh dependency di endpoint)
        """
        admin_client = await self._get_admin_client()
        
        try:
            await canvas_queries.delete_canvas_db(
                admin_client=admin_client,
                canvas_id=canvas_id
            )
            # Sukses, tidak mengembalikan apa-apa
            
        except (NotFoundError, DatabaseError) as e:
            logger.warning(f"Gagal hapus canvas {canvas_id}: {e}")
            raise
    
    async def get_canvas_blocks(
        self, 
        canvas_id: UUID, 
        limit: int = 100, 
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Mendapatkan daftar block di canvas.
        (Akses di-handle oleh dependency di endpoint)
        """
        admin_client = await self._get_admin_client()
        
        try:
            blocks = await canvas_queries.get_canvas_blocks_db_rpc(
                admin_client=admin_client,
                canvas_id=canvas_id,
                limit=limit,
                offset=offset
            )
            return blocks
        except DatabaseError as e:
            logger.error(f"Gagal mengambil block canvas {canvas_id}: {e}", exc_info=True)
            raise
    
    async def get_canvas_with_access(
        self, 
        canvas_id: UUID
    ) -> Dict[str, Any]:
        """
        Mendapatkan canvas dengan informasi akses user.
        (Akses *tidak* di-handle dependency, fungsi ini
         digunakan oleh dependency itu sendiri)
        """
        admin_client = await self._get_admin_client()
        
        try:
            access_info = await canvas_queries.get_canvas_with_access_db(
                admin_client=admin_client,
                canvas_id=canvas_id,
                user_id=self.user.id
            )
            return access_info
        except (NotFoundError, DatabaseError) as e:
            logger.debug(f"Gagal mengambil canvas/akses untuk {canvas_id}: {e}")
            raise