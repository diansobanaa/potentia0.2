# backend/app/db/queries/conversation/conversation_queries.py
import logging
import asyncio 
from uuid import UUID
from typing import Optional, Dict, Any
from supabase import Client
from postgrest import APIResponse
from app.core.exceptions import DatabaseError, NotFoundError


logger = logging.getLogger(__name__)
def get_or_create_conversation(
    authed_client: Client,
    user_id: UUID,
    conversation_id: Optional[UUID] = None
) -> Dict[str, Any]:
    """
    Mencari conversation_id, atau membuat baru jika ID = None.
    Selalu mengembalikan dict dengan kunci 'conversation_id'.
    """
    try:
        # --- BLOK SELECT ---
        if conversation_id:
            response: APIResponse = authed_client.table("conversations") \
                .select("*") \
                .eq("user_id", str(user_id)) \
                .eq("conversation_id", str(conversation_id)) \
                .single() \
                .execute()

            if response.data:
                # Pastikan selalu ada 'conversation_id'
                if "conversation_id" not in response.data:
                    raise Exception("Kolom 'conversation_id' tidak ditemukan pada hasil SELECT.")
                return response.data

        # --- BLOK INSERT ---
        logger.debug(f"Membuat conversation baru untuk user {user_id}")
        insert_payload = {
            "user_id": str(user_id),
            "title": "New Chat"
        }

        response: APIResponse = authed_client.table("conversations") \
            .insert(insert_payload, returning="representation") \
            .execute()

        if not response.data or not isinstance(response.data, list):
            raise Exception("Gagal membuat percakapan baru atau respons tidak valid.")

        data = response.data[0]
        if "conversation_id" not in data:
            raise Exception("Kolom 'conversation_id' tidak ditemukan pada hasil INSERT.")

        return data

    except Exception as e:
        logger.error(f"Error di get_or_create_conversation: {e}", exc_info=True)
        raise


async def update_conversation_title(
    authed_client: Client,
    user_id: UUID,
    conversation_id: UUID,
    new_title: str
) -> Dict[str, Any]:
    """
    Memperbarui 'title' dari sebuah conversation_id milik user_id.
    Dijalankan secara non-blocking menggunakan asyncio.to_thread.
    """
    
    def sync_db_call() -> Dict[str, Any]:
        """Fungsi sinkron untuk dijalankan di thread terpisah."""
        try:
            response: APIResponse = (
                authed_client.table("conversations")
                .update({"title": new_title}, returning="representation")
                .eq("user_id", str(user_id))
                .eq("conversation_id", str(conversation_id))
                .execute()
            )

            # Supabase mengembalikan list di response.data
            if not response.data or len(response.data) == 0:
                logger.warning(f"Gagal update judul: Percakapan {conversation_id} tidak ditemukan atau bukan milik user {user_id}.")
                raise NotFoundError("Percakapan tidak ditemukan atau Anda tidak memiliki akses.")

            data = response.data[0]
            return data
        
        except NotFoundError:
             raise
        except Exception as e:
            # [DIUBAH] Tangkap AttributeError secara spesifik jika masih terjadi
            if isinstance(e, AttributeError):
                 logger.error(f"AttributeError saat update (sync) {conversation_id}: {e}", exc_info=True)
                 raise DatabaseError("update_title_syntax", str(e))
            logger.error(f"Error saat update judul (sync) untuk {conversation_id}: {e}", exc_info=True)
            raise DatabaseError("update_title_generic", str(e))
    
    try:
        updated_data = await asyncio.to_thread(sync_db_call)
        logger.info(f"Judul untuk percakapan {conversation_id} berhasil diperbarui.")
        return updated_data
    
    except Exception as e:
        logger.error(f"Error di update_conversation_title (async) untuk {conversation_id}: {e}", exc_info=True)
        if isinstance(e, (DatabaseError, NotFoundError)):
            raise 
        raise DatabaseError("update_title_async", f"Error tidak terduka: {str(e)}")