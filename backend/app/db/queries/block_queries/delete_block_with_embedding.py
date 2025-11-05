from typing import Dict, Any, Optional
from uuid import UUID
from supabase import Client as SupabaseClient
from postgrest.exceptions import APIError

async def delete_block_with_embedding(
    authed_client: SupabaseClient, 
    block_id: UUID
) -> bool:
    """
    Menghapus block dari tabel 'Blocks' dan juga menghapus 
    embedding terkait dari tabel 'BlocksEmbeddings'.
    Idealnya gunakan trigger DB (ON DELETE CASCADE), tapi ini versi Python.
    """
    embedding_deleted = False
    try:
        # 1. Hapus embedding dari tabel BlocksEmbeddings terlebih dahulu
        print(f"(Query/Delete) Deleting embedding for block {block_id}")
        embed_response = authed_client.table("BlocksEmbeddings") \
            .delete() \
            .eq("block_id", str(block_id)) \
            .execute()
        # Delete mungkin tidak mengembalikan data, anggap sukses jika tidak error
        embedding_deleted = True 
        print(f"(Query/Delete) Embedding deletion attempt finished for block {block_id}.")
    except APIError as e:
        print(f"(Query/Delete) APIError deleting embedding for block {block_id}: {e}")
        # Lanjutkan hapus block utama meskipun embedding gagal dihapus? Tergantung kebutuhan.
    except Exception as e:
        print(f"(Query/Delete) Unexpected error deleting embedding for block {block_id}: {e}")
        # Lanjutkan?

    block_deleted = False
    try:
        # 2. Hapus block utama dari tabel Blocks
        print(f"(Query/Delete) Deleting base block {block_id}")
        response = authed_client.table("Blocks") \
            .delete() \
            .eq("block_id", str(block_id)) \
            .execute()
        block_deleted = bool(response and response.data)
        if block_deleted:
            print(f"(Query/Delete) Base block {block_id} deleted successfully.")
        else:
             print(f"(Query/Delete) Base block {block_id} not found or failed to delete.")

    except APIError as e:
        print(f"(Query/Delete) APIError deleting base block {block_id}: {e}")
    except Exception as e:
        print(f"(Query/Delete) Unexpected error deleting base block {block_id}: {e}")

    # Kembalikan True jika block utama berhasil dihapus
    return block_deleted