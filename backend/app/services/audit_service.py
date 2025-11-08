# File: backend/app/services/audit_service.py
# (Diperbarui dengan 'await' yang hilang)

from uuid import UUID
import logging
# --- PERBAIKAN: Impor klien admin async ---
from app.db.supabase_client import get_supabase_admin_async_client
# ------------------------------------------

logger = logging.getLogger(__name__)

async def log_action(user_id: UUID, action: str, details: dict):
    """
    (Async Native) Menyimpan log audit ke database.
    Ini sekarang harus di 'await' oleh pemanggilnya.
    """
    try:
        # --- PERBAIKAN: 'await' panggilan untuk mendapatkan klien ---
        admin_client = await get_supabase_admin_async_client()
        # ----------------------------------------------------
        
        await admin_client.table("AuditLog").insert({
            "user_id": str(user_id), "action": action, "details": details
        }).execute()
        
    except Exception as e:
        # Log error tapi jangan gagalkan request utama
        logger.error(f"CRITICAL: Gagal menyimpan AUDIT LOG (async): {e}", exc_info=True)