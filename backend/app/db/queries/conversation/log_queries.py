# backend/app/db/queries/conversation/log_queries.py
# (Diperbarui untuk AsyncClient native + perbaikan NameError)

import logging
from postgrest.exceptions import APIError
from datetime import datetime
import uuid
# --- PERBAIKAN: Impor AsyncClient ---
from supabase.client import AsyncClient
from typing import List, Dict, Any, Optional
# --- PERBAIKAN: Impor UUID yang hilang ---
from uuid import UUID
# ------------------------------------

logger = logging.getLogger(__name__)

async def get_recent_decisions(
    authed_client: AsyncClient, # <-- Tipe diubah
    user_id: UUID, # <-- Sekarang 'UUID' dikenali
    conversation_id: UUID, 
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    (Async Native) Ambil beberapa log keputusan terakhir.
    """
    try:
        # --- PERBAIKAN: Gunakan 'await' ---
        response = await (
            authed_client.table("decision_logs")
            .select("*")
            .eq("user_id", str(user_id))
            .eq("conversation_id", str(conversation_id))
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        data = response.data or []
        if not data:
            logger.info("ℹ️ Tidak ada log keputusan ditemukan untuk percakapan ini.")
        return data
    except Exception as e:
        logger.error(f"Gagal memuat riwayat keputusan (async): {e}", exc_info=True)
        return []

async def create_decision_log_safe(
    authed_client: AsyncClient, # <-- Tipe diubah
    user_id: Optional[UUID],
    conversation_id: Optional[UUID],
    message_id: Optional[UUID],
    context_id: Optional[UUID],
    decision_reason: Optional[str],
    details_json: Optional[Dict[str, Any]],
):
    """
    (Async Native) Simpan keputusan AI Judge ke tabel decision_logs.
    """
    try:
        safe_user_id = str(user_id) if user_id else "00000000-0000-0000-0000-000000000000"
        safe_conv_id = str(conversation_id) if conversation_id else str(uuid.uuid4())
        safe_msg_id = str(message_id) if message_id else str(uuid.uuid4())
        safe_ctx_id = str(context_id) if context_id else str(uuid.uuid4())
        safe_reason = decision_reason or "Tidak ada reason dari AI."
        safe_details = details_json or {}

        # --- PERBAIKAN: Gunakan 'await' ---
        response = await (
            authed_client.table("decision_logs")
            .insert({
                "user_id": safe_user_id,
                "conversation_id": safe_conv_id,
                "message_id": safe_msg_id,
                "chosen_context_id": safe_ctx_id,
                "decision_reason": safe_reason,
                "details": safe_details,
                "created_at": datetime.utcnow().isoformat(),
            })
            .execute()
        )

        if response.data:
            logger.info(f"✅ Log keputusan berhasil disimpan ({safe_msg_id}) ke decision_logs.")
        else:
            logger.warning("⚠️ Insert log keputusan berhasil tapi tidak ada data dikembalikan.")
        return response.data

    except APIError as e:
        logger.error(f"❌ Error API di create_decision_log_safe (async): {e.details if hasattr(e, 'details') else e}")
    except Exception as e:
        logger.error(f"❌ Error umum di create_decision_log_safe (async): {e}", exc_info=True)