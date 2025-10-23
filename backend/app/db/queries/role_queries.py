from typing import Optional, List

# Tambahkan 'authed_client' sebagai argumen pertama
def find_relevant_role(authed_client, query_embedding: List[float]) -> Optional[dict]:
    """
    Memanggil fungsi RPC Supabase 'find_most_relevant_role' untuk mencari role yang paling relevan
    berdasarkan embedding query.
    Menggunakan klien Supabase yang sudah diautentikasi.
    """
    try:
        # Gunakan 'authed_client' untuk memanggil RPC
        response = authed_client.rpc("find_most_relevant_role", {"query_embedding": query_embedding}).execute()
        
        # Kembalikan hasil pertama jika ada, atau None jika tidak ada
        return response.data[0] if response.data else None
    except Exception as e:
        # Tambahkan penanganan error jika RPC gagal
        print(f"Error calling find_most_relevant_role RPC: {e}")
        return None

# TODO: Jika ada fungsi lain di file ini, perbarui juga untuk menerima dan menggunakan 'authed_client'.