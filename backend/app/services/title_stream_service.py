# backend/app/services/title_stream_service.py
# (Diperbarui untuk panggilan DB async native)

import logging
import asyncio
import json
from uuid import UUID
from typing import AsyncGenerator, Dict, Any
# --- PERBAIKAN: Impor AsyncClient ---
from supabase.client import AsyncClient
# ------------------------------------

from app.services.ai.deepseek_client import deepseek_client
from app.db.queries.conversation.message_queries import get_first_turn_messages
from app.core.exceptions import NotFoundError

logger = logging.getLogger(__name__)

class TitleStreamService:
    def __init__(self, auth_info: Dict[str, Any]):
        self.user = auth_info["user"]
        self.client: AsyncClient = auth_info["client"] # <-- Tipe diubah
        logger.debug(f"TitleStreamService (Async) diinisialisasi untuk User: {self.user.id}")

    async def _update_conversation_title_in_db(self, conversation_id: UUID, new_title: str):
        """
        [PERBAIKAN] Menjalankan update DB secara async native.
        """
        logger.info(f"Menjalankan update judul (async native) untuk convo: {conversation_id}")
        
        try:
            # --- PERBAIKAN: Hapus 'sync_db_call' dan 'asyncio.to_thread' ---
            await self.client.table("conversations") \
                .update({"title": new_title}) \
                .eq("conversation_id", str(conversation_id)) \
                .eq("user_id", str(self.user.id)) \
                .execute() # <-- 'await'
            logger.info(f"Update judul berhasil untuk {conversation_id}")
        except Exception as e:
            logger.error(f"Gagal update judul (async native) untuk {conversation_id}: {e}", exc_info=True)

    async def orchestrate_streaming_title(
        self, 
        conversation_id: UUID
    ) -> AsyncGenerator[str, None]:
        user_id = self.user.id
        logger.info(f"Memulai stream judul untuk user {user_id}, convo {conversation_id}.")
        
        try:
            # --- PERBAIKAN: Panggil kueri async (yang sudah di-refaktor) ---
            user_message, ai_response = await get_first_turn_messages(
                self.client,
                user_id,
                conversation_id
            ) # <-- 'await'
            
            if not user_message or not ai_response:
                raise NotFoundError("Data pesan awal tidak ditemukan untuk pembuatan judul.")

        except Exception as e:
            logger.error(f"Gagal mengambil pesan awal untuk stream judul: {e}", exc_info=True)
            error_payload = {"type": "error", "detail": str(e)}
            yield json.dumps(error_payload) + "\n"
            return

        # (Sisa logika streaming dari DeepSeek/Gemini tidak berubah)
        full_title_chunks = []
        try:
            async for title_chunk in deepseek_client.stream_title_from_deepseek(
                user_message=user_message,
                ai_response=ai_response
            ):
                full_title_chunks.append(title_chunk)
                chunk_payload = {"type": "title_chunk", "content": title_chunk}
                yield json.dumps(chunk_payload) + "\n"
        
        except Exception as e:
            logger.error(f"Error saat streaming dari DeepSeek: {e}", exc_info=True)
            error_payload = {"type": "error", "detail": f"Error AI Judul: {str(e)}"}
            yield json.dumps(error_payload) + "\n"
        
        final_title = "".join(full_title_chunks).strip()
        
        if final_title and "[Error" not in final_title:
            await self._update_conversation_title_in_db(conversation_id, final_title)
        else:
            logger.warning(f"Stream judul selesai tetapi hasilnya kosong atau error, update DB dilewati.")