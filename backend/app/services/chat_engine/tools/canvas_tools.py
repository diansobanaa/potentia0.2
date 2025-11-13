# File: backend/app/services/chat_engine/tools/canvas_tools.py
# (v3.3 - Refactor untuk memutus circular import)

import logging
from uuid import UUID, uuid4
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.tools import tool

# Impor kueri atomik
from app.db.queries.canvas import block_queries
from app.db.supabase_client import get_supabase_admin_async_client
from app.services.redis_rate_limiter import rate_limiter
# [HAPUS] Hapus impor yang menyebabkan circular dependency
# from app.core.dependencies import AuthInfoDep

logger = logging.getLogger(__name__)

# [CATATAN] Pydantic model ini tidak lagi digunakan secara langsung oleh tool,
# tapi bisa berguna untuk validasi di masa depan.
class CreateBlockToolInput(BaseModel):
    canvas_id: str = Field(..., description="ID Canvas target (UUID).")
    content: str = Field(..., description="Konten teks untuk blok baru.")
    block_type: str = Field(default="text", description="Tipe blok (misal: 'text', 'heading_1').")
    parent_id: Optional[str] = Field(None, description="ID blok induk (opsional).")
    y_position: Optional[str] = Field(None, description="Posisi (LexoRank). Jika None, akan ditambahkan di akhir.")

@tool
async def create_canvas_block(
    content: str,
    canvas_id: str,
    # [FIX] Argumen yang dibutuhkan disuntikkan oleh ToolExecutor, bukan dari FastAPI
    auth_info: Dict[str, Any],
    request_id: str,
    block_type: str = "text",
    parent_id: Optional[str] = None,
    y_position: Optional[str] = None, # Mengganti y_order
    # Argumen x dan y tidak digunakan di logika, jadi bisa diabaikan untuk saat ini
    **kwargs,
) -> str:
    """
    Tool untuk membuat SATU blok baru di canvas.
    Tool ini idempotent, artinya panggilan berulang dengan argumen yang sama tidak akan membuat duplikat.
    """
    logger.info(f"REQUEST_ID: {request_id} - Tool 'create_canvas_block' dipanggil.")

    # === Implementasi Idempotency ===
    # Kunci unik berdasarkan request ID dan konten
    lock_key = f"lock:tool:{request_id}:create_block:{canvas_id}:{content[:50]}"
    try:
        is_new_request = await rate_limiter.redis.set(lock_key, "1", nx=True, ex=3600) # Lock berlaku 1 jam
        if not is_new_request:
            logger.warning(f"REQUEST_ID: {request_id} - Terdeteksi duplikat (create_canvas_block), eksekusi dibatalkan.")
            return f"Info: Blok dengan konten '{content[:30]}...' sudah pernah diproses untuk permintaan ini."
    except Exception as e:
        logger.error(f"REQUEST_ID: {request_id} - Gagal mengecek idempotency lock di Redis: {e}. Melanjutkan dengan risiko...")
    # === Akhir Idempotency Check ===

    try:
        # [FIX] Ambil user_id dari auth_info yang disuntikkan
        user_id = UUID(auth_info["user"]["id"])
        admin_client = await get_supabase_admin_async_client()

        # Gunakan RPC atomik yang sudah ada
        rpc_params = {
            "p_block_id": str(uuid4()),
            "p_canvas_id": str(UUID(canvas_id)),
            "p_client_op_id": f"{request_id}-{str(uuid4())[:4]}", # Idempotency key unik per blok
            "p_user_id": str(user_id),
            "p_action": "create",
            "p_parent_id": str(UUID(parent_id)) if parent_id else None,
            "p_y_order": y_position, # [FIX] Menggunakan argumen baru
            "p_type": block_type, # [FIX] Menggunakan argumen, bukan built-in `type`
            "p_content": content,
        }

        result = await block_queries.execute_mutation_rpc(admin_client, rpc_params)

        if result.get("status") == "success":
            return f"Sukses: Blok '{content[:30]}...' berhasil dibuat di canvas."
        else:
            error_message = result.get('error', 'Gagal menjalankan RPC')
            logger.error(f"REQUEST_ID: {request_id} - Gagal membuat blok: {error_message}")
            return f"Error: Gagal membuat blok. Detail: {error_message}"

    except Exception as e:
        logger.error(f"REQUEST_ID: {request_id} - Error kritis saat eksekusi create_canvas_block: {e}", exc_info=True)
        # Hapus lock jika terjadi error agar bisa di-retry
        await rate_limiter.redis.delete(lock_key)
        return f"Error Kritis: Terjadi kesalahan tak terduga saat mencoba membuat blok. Detail: {e}"
