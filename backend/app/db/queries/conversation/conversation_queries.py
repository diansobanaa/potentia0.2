# backend/app/db/queries/conversation/conversation_queries.py
import logging
from uuid import UUID
from typing import Optional, Dict, Any
from supabase import Client
from postgrest import APIResponse

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
