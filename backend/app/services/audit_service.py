# File: backend/app/services/audit_service.py
# (DIPERBAIKI - Typo nama tabel)

from uuid import UUID
import logging
from app.db.supabase_client import get_supabase_admin_async_client

logger = logging.getLogger(__name__)

async def log_action(user_id: UUID, action: str, details: dict):
    """
    (Async Native) Menyimpan log audit ke database.
    Sumber:
    """
    try:
        admin_client = await get_supabase_admin_async_client()
        
        # [PERBAIKAN] Menggunakan nama tabel 'SystemAudit' dari blueprint,
        # bukan 'AuditLog'
        response = await admin_client.table("SystemAudit").insert({
            "user_id": str(user_id), 
            "action": action, 
            "details": details,
            "entity": details.get("entity_type", "unknown"), # Wajib diisi (sesuai blueprint)
            "entity_id": details.get("entity_id"),
            "status": "success" # Asumsikan sukses jika dipanggil
        }).execute()
        
    except Exception as e:
        # Log error tapi jangan gagalkan request utama
        logger.error(f"CRITICAL: Gagal menyimpan AUDIT LOG (async): {e}", exc_info=True)