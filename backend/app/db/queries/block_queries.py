from typing import List, Optional
from uuid import UUID

def create_block(authed_client, canvas_id: UUID, block_data: dict) -> Optional[dict]:
    """
    Membuat block baru di tabel 'Blocks' menggunakan klien yang diautentikasi.
    """
    response = authed_client.table("Blocks").insert({**block_data, "canvas_id": str(canvas_id)}).execute()
    return response.data[0] if response.data else None

def get_blocks_in_canvas(authed_client, canvas_id: UUID) -> List[dict]:
    """
    Mengambil semua block dalam canvas menggunakan klien yang diautentikasi.
    """
    response = authed_client.table("Blocks").select("*").eq("canvas_id", str(canvas_id)).order("y_order").execute()
    return response.data if response.data else []

def update_block(authed_client, block_id: UUID, update_data: dict) -> Optional[dict]:
    """
    Memperbarui block tertentu menggunakan klien yang diautentikasi.
    """
    response = authed_client.table("Blocks").update(update_data).eq("block_id", str(block_id)).execute()
    return response.data[0] if response.data else None

def delete_block(authed_client, block_id: UUID) -> bool:
    """
    Menghapus block tertentu menggunakan klien yang diautentikasi.
    """
    response = authed_client.table("Blocks").delete().eq("block_id", str(block_id)).execute()
    return len(response.data) > 0
