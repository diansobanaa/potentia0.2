# backend/app/db/queries/conversation/conversation_queries.py
# (Diperbarui untuk AsyncClient native)

import logging
import asyncio 
from uuid import UUID
from typing import Optional, Dict, Any
# --- PERBAIKAN: Impor AsyncClient ---
from supabase.client import AsyncClient
from postgrest import APIResponse
from app.core.exceptions import DatabaseError, NotFoundError

logger = logging.getLogger(__name__)

async def get_or_create_conversation(
    authed_client: AsyncClient, # <-- Tipe diubah
    user_id: UUID,
    conversation_id: Optional[UUID] = None
) -> Dict[str, Any]:
    """
    (Async Native) Mencari conversation, atau membuat baru.
    """
    try:
        if conversation_id:
            # --- PERBAIKAN: Gunakan 'await' ---
            response: APIResponse = await authed_client.table("conversations") \
                .select("*") \
                .eq("user_id", str(user_id)) \
                .eq("conversation_id", str(conversation_id)) \
                .single() \
                .execute()

            if response.data:
                if "conversation_id" not in response.data:
                    raise Exception("Kolom 'conversation_id' tidak ditemukan.")
                return response.data

        logger.debug(f"Membuat conversation baru untuk user {user_id}")
        insert_payload = {
            "user_id": str(user_id),
            "title": "New Chat"
        }

        # --- PERBAIKAN: Gunakan 'await' ---
        response: APIResponse = await authed_client.table("conversations") \
            .insert(insert_payload, returning="representation") \
            .execute()

        if not response.data or not isinstance(response.data, list):
            raise Exception("Gagal membuat percakapan baru atau respons tidak valid.")

        data = response.data[0]
        if "conversation_id" not in data:
            raise Exception("Kolom 'conversation_id' tidak ditemukan pada hasil INSERT.")

        return data

    except Exception as e:
        logger.error(f"Error di get_or_create_conversation (async): {e}", exc_info=True)
        raise DatabaseError(f"Error di get_or_create_conversation: {str(e)}")


async def update_conversation_title(
    authed_client: AsyncClient,
    user_id: UUID,
    conversation_id: UUID,
    new_title: str
) -> Dict[str, Any]:
    try:
        # --- PERBAIKAN: Hapus .single() ---
        response: APIResponse = await (
            authed_client.table("conversations")
            .update({"title": new_title}, returning="representation")
            .eq("user_id", str(user_id))
            .eq("conversation_id", str(conversation_id))
            .execute()
        )
        # ---------------------------------
        if not response.data or len(response.data) == 0:
            raise NotFoundError("Percakapan tidak ditemukan atau Anda tidak memiliki akses.")
        return response.data[0]
    except Exception as e:
        if isinstance(e, (DatabaseError, NotFoundError)): raise 
        raise DatabaseError("update_title_async", f"Error tidak terduka: {str(e)}")