from typing import List, Optional, Dict, Any
from uuid import UUID
from postgrest.exceptions import APIError
from supabase import Client as SupabaseClient

def get_blocks_in_canvas(authed_client: SupabaseClient, canvas_id: UUID) -> List[dict]:
    """
    Mengambil semua block dalam canvas tertentu, diurutkan berdasarkan y_order.
    Menggunakan klien Supabase yang sudah diautentikasi.
    """
    try:
        # Menggunakan authed_client untuk query ke tabel Blocks
        response = authed_client.table("Blocks") \
            .select("*") \
            .eq("canvas_id", str(canvas_id)) \
            .order("y_order") \
            .execute()
        # Mengembalikan data jika ada, atau list kosong jika tidak ada atau error
        return response.data if response and response.data else []
    except APIError as e:
        # Log error jika terjadi masalah saat query
        print(f"(Query/Get) APIError getting blocks in canvas {canvas_id}: {e}")
        return [] # Kembalikan list kosong saat error
    except Exception as e:
        # Tangani error tak terduga lainnya
        print(f"(Query/Get) Unexpected error getting blocks in canvas {canvas_id}: {e}")
        return []

def get_block_by_id(authed_client: SupabaseClient, block_id: UUID) -> Optional[Dict[str, Any]]:
     """
     Mengambil satu block berdasarkan ID-nya.
     Menggunakan klien Supabase yang sudah diautentikasi.
     """
     try:
        # Menggunakan authed_client untuk query ke tabel Blocks
        # maybe_single() digunakan agar tidak error jika block tidak ditemukan
        response = authed_client.table("Blocks").select("*").eq("block_id", str(block_id)).maybe_single().execute()
        # Mengembalikan data jika ada, atau None jika tidak ditemukan atau error
        return response.data if response and response.data else None
     except APIError as e:
        # Log error jika terjadi masalah saat query
        print(f"(Query/Get) APIError getting block {block_id}: {e}")
        return None # Kembalikan None saat error
     except Exception as e:
        # Tangani error tak terduga lainnya
        print(f"(Query/Get) Unexpected error getting block {block_id}: {e}")
        return None
