#backend\app\services\title_stream_service.py
import logging
import asyncio
import json
from uuid import UUID
from typing import AsyncGenerator, Dict, Any
from supabase import Client as SupabaseClient

# Impor dari project Anda
from app.services.ai.deepseek_client import deepseek_client
from app.db.queries.conversation.message_queries import get_first_turn_messages
from app.core.exceptions import NotFoundError

logger = logging.getLogger(__name__)

class TitleStreamService:
    """
    Menangani logika untuk streaming judul dan memperbarui database.
    """
    
    def __init__(self, auth_info: Dict[str, Any]):
        self.user = auth_info["user"]
        self.client: SupabaseClient = auth_info["client"]
        logger.debug(f"TitleStreamService diinisialisasi untuk User: {self.user.id}")

    async def _update_conversation_title_in_db(self, conversation_id: UUID, new_title: str):
        """
        Menjalankan update DB di thread terpisah.
        Ini memenuhi permintaan Anda untuk logika update "langsung di service".
        """
        logger.info(f"Menjalankan update judul di thread terpisah untuk convo: {conversation_id}")
        
        def sync_db_call():
            """Fungsi sinkron untuk dijalankan di thread."""
            try:
                response = self.client.table("conversations") \
                    .update({"title": new_title}) \
                    .eq("conversation_id", str(conversation_id)) \
                    .eq("user_id", str(self.user.id)) \
                    .execute()
                logger.info(f"Update judul berhasil untuk {conversation_id}, data: {response.data}")
            except Exception as e:
                logger.error(f"Gagal update judul (sync) untuk {conversation_id}: {e}", exc_info=True)

        try:
            # Menjalankan I/O sinkron di thread terpisah agar tidak memblokir
            await asyncio.to_thread(sync_db_call)
        except Exception as e:
            logger.error(f"Error saat menjalankan asyncio.to_thread untuk update judul: {e}")

    async def orchestrate_streaming_title(
        self, 
        conversation_id: UUID
    ) -> AsyncGenerator[str, None]:
        """
        Async Generator utama untuk Endpoint B (Title Stream).
        Menghasilkan string ndjson (json per baris).
        """
        user_id = self.user.id
        logger.info(f"Memulai stream judul untuk user {user_id}, convo {conversation_id}.")
        
        try:
            # 1. Ambil pesan pertama (User & AI) dari DB
            user_message, ai_response = await asyncio.to_thread(
                get_first_turn_messages,
                self.client,
                user_id,
                conversation_id
            )
            
            if not user_message or not ai_response:
                raise NotFoundError("Data pesan awal tidak ditemukan untuk pembuatan judul.")

        except Exception as e:
            logger.error(f"Gagal mengambil pesan awal untuk stream judul: {e}", exc_info=True)
            error_payload = {"type": "error", "detail": str(e)}
            yield json.dumps(error_payload) + "\n"
            return

        # 2. Panggil DeepSeek Client (Langkah 2) dan stream hasilnya
        full_title_chunks = []
        try:
            async for title_chunk in deepseek_client.stream_title_from_deepseek(
                user_message=user_message,
                ai_response=ai_response
            ):
                full_title_chunks.append(title_chunk)
                # Kirim chunk ke frontend
                chunk_payload = {"type": "title_chunk", "content": title_chunk}
                yield json.dumps(chunk_payload) + "\n"
        
        except Exception as e:
            logger.error(f"Error saat streaming dari DeepSeek: {e}", exc_info=True)
            error_payload = {"type": "error", "detail": f"Error AI Judul: {str(e)}"}
            yield json.dumps(error_payload) + "\n"
        
        # 3. Setelah stream selesai, jalankan update DB
        final_title = "".join(full_title_chunks).strip()
        
        if final_title and "[Error" not in final_title:
            # Kita 'await' ini untuk memastikan update terjadi sebelum fungsi selesai
            await self._update_conversation_title_in_db(conversation_id, final_title)
        else:
            logger.warning(f"Stream judul selesai tetapi hasilnya kosong atau error, update DB dilewati.")