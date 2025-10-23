from typing import List, Optional
from uuid import UUID
# Hapus impor klien global jika masih ada
# from app.db.supabase_client import get_supabase_client
from postgrest.exceptions import APIError # Impor APIError untuk penanganan error spesifik

# Fungsi ini akan dipanggil oleh endpoint Anda
def get_or_create_conversation(authed_client, canvas_id: Optional[UUID], user_id: Optional[UUID]) -> Optional[dict]:
    """
    Mencari conversation yang ada berdasarkan canvas_id dan user_id (jika ada).
    Jika tidak ditemukan, membuat conversation baru.
    Menggunakan klien Supabase yang sudah diautentikasi.
    """
    # Membangun query dasar untuk mencari conversation di tabel "Conversations"
    # Pastikan nama tabel "Conversations" sudah benar
    query = authed_client.table("Conversations").select("*").eq("canvas_id", str(canvas_id))

    # Sesuaikan query berdasarkan apakah user_id ada (pengguna terdaftar) atau None (tamu)
    if user_id:
        # Jika ada user_id, cari conversation yang cocok dengan user_id tersebut
        query = query.eq("user_id", str(user_id))
    else:
        # Jika tidak ada user_id (tamu), cari conversation yang user_id-nya NULL
        query = query.is_("user_id", None) # Menggunakan None untuk mencocokkan IS NULL

    try:
        # Coba eksekusi query untuk mencari conversation yang sudah ada.
        # maybe_single() akan mengembalikan satu baris atau None, tanpa error jika 0 baris.
        response = query.maybe_single().execute()

        # PERBAIKAN PENTING: Periksa apakah 'response' TIDAK None SEBELUM mengakses 'response.data'
        if response and response.data:
            # Jika conversation ditemukan (response ada dan berisi data), kembalikan datanya
            return response.data

    except APIError as e:
        # Tangani error spesifik jika terjadi saat query SELECT
        print(f"APIError checking for existing conversation: {e}")
        # Jika terjadi error saat SELECT, mungkin ada masalah koneksi atau query. Kita raise lagi.
        raise e
    except Exception as e:
        # Tangani error umum lainnya saat SELECT
        print(f"Unexpected error checking for existing conversation: {e}")
        raise e

    # --- Bagian ini hanya dijalankan jika conversation TIDAK ditemukan ---
    # Buat payload (data) untuk conversation baru
    new_conv_payload = {"canvas_id": str(canvas_id)}
    if user_id:
        # Tambahkan user_id ke payload jika pengguna terdaftar
        new_conv_payload["user_id"] = str(user_id)
        
    try:
        # Coba buat conversation baru menggunakan INSERT
        # Pastikan nama tabel "Conversations" sudah benar
        new_conv_response = authed_client.table("Conversations").insert(new_conv_payload).execute()
        
        # Kembalikan data conversation baru jika berhasil dibuat
        # Periksa apakah response ada dan berisi data sebelum mengakses index [0]
        return new_conv_response.data[0] if new_conv_response and new_conv_response.data else None
    except APIError as e:
        # Tangani error spesifik jika terjadi saat INSERT
        print(f"APIError creating new conversation: {e}")
        raise e
    except Exception as e:
        # Tangani error umum lainnya saat INSERT
        print(f"Unexpected error creating new conversation: {e}")
        raise e

# --- Fungsi-fungsi lain (sudah disesuaikan dengan authed_client) ---

def find_relevant_history(authed_client, query_embedding: List[float]) -> List[dict]:
    """
    Memanggil fungsi RPC Supabase ('find_relevant_conversation_history') 
    untuk mencari riwayat pesan yang relevan berdasarkan embedding query.
    Menggunakan klien Supabase yang sudah diautentikasi.
    """
    try:
        # Memanggil fungsi RPC menggunakan 'authed_client'
        # Nama RPC sudah sesuai dengan SQL Anda
        response = authed_client.rpc("find_relevant_conversation_history", {"query_embedding": query_embedding}).execute()
        # Kembalikan data jika ada, atau list kosong jika tidak atau jika response None
        return response.data if response and response.data else []
    except APIError as e:
        # Tangani error spesifik dari Supabase/PostgREST saat memanggil RPC
        print(f"APIError calling find_relevant_conversation_history RPC: {e}")
        # Jika error karena tabel tidak ada (sering terjadi jika RPC belum dibuat/salah), beri pesan
        if e.code == '42P01': # Kode PostgreSQL untuk 'undefined_table' atau 'undefined_function'
             # PERIKSA: Pastikan tabel 'Messages' benar-benar ada di Supabase
             print("Pastikan tabel 'public.Messages' ada DAN fungsi RPC 'find_relevant_conversation_history' sudah dibuat di Supabase.")
        return [] # Kembalikan list kosong jika terjadi error
    except Exception as e:
        # Tangani error umum lainnya
        print(f"Unexpected error calling find_relevant_conversation_history RPC: {e}")
        return []

def add_message(authed_client, conversation_id: UUID, role: str, content: str, embedding: Optional[List[float]]) -> Optional[dict]:
    """
    Menyimpan pesan baru (user atau AI) beserta embeddingnya ke tabel 'Messages'.
    Menggunakan klien Supabase yang sudah diautentikasi.
    """
    # Siapkan payload dasar untuk pesan
    payload = {
        "conversation_id": str(conversation_id),
        "role": role,
        "content": content,
    }
    # Hanya tambahkan embedding ke payload jika nilainya ada (bukan None)
    if embedding:
        # Pastikan nama kolom 'vector_embedding' sudah benar sesuai skema tabel 'Messages' Anda
        payload["vector_embedding"] = embedding 

    try:
        # Coba masukkan data pesan baru menggunakan INSERT
        # PERIKSA: Menggunakan nama tabel "Messages" (M besar) sesuai SQL Anda
        response = authed_client.table("Messages").insert(payload).execute() 
        # Kembalikan data pesan yang baru dibuat jika berhasil
        return response.data[0] if response and response.data else None
    except APIError as e:
        # Tangani error spesifik dari Supabase/PostgREST saat INSERT
        print(f"APIError adding message: {e}")
         # Jika error karena tabel tidak ada, beri pesan lebih jelas
        if e.code == '42P01': 
             # PERIKSA: Pastikan tabel 'Messages' benar-benar ada di Supabase
             print("Pastikan tabel 'public.Messages' ada di database Supabase.")
        return None # Kembalikan None jika terjadi error saat menyimpan
    except Exception as e:
        # Tangani error umum lainnya
        print(f"Unexpected error adding message: {e}")
        return None

def claim_guest_session(authed_client, conversation_id: UUID, user_id: UUID) -> bool:
    """
    Mengupdate conversation tamu (yang sebelumnya user_id=NULL) 
    untuk dihubungkan ke user_id pengguna yang baru login/daftar.
    Menggunakan klien Supabase yang sudah diautentikasi.
    """
    try:
        # Coba update kolom 'user_id' di tabel 'Conversations'
        # Pastikan nama tabel "Conversations" sudah benar
        response = authed_client.table("Conversations").update({"user_id": str(user_id)}).eq("conversation_id", str(conversation_id)).execute()
        # Periksa apakah update berhasil (ada data yang dikembalikan atau indikasi lain)
        # Cara paling aman adalah memeriksa apakah response ada dan datanya tidak kosong
        return bool(response and response.data) 
    except APIError as e:
        # Tangani error spesifik dari Supabase/PostgREST saat UPDATE
        print(f"APIError claiming guest session: {e}")
        return False # Kembalikan False jika gagal
    except Exception as e:
        # Tangani error umum lainnya
        print(f"Unexpected error claiming guest session: {e}")
        return False

def get_all_conversation_summaries(authed_client, user_id: UUID) -> List[dict]:
    """
    Mengambil daftar ringkasan percakapan (summaries) dari pengguna tertentu.
    Menggunakan klien Supabase yang sudah diautentikasi.
    """
    try:
        # Query tabel 'ConversationSummaries'
        # Pastikan nama tabel "ConversationSummaries" sudah benar
        response = authed_client.table("ConversationSummaries") \
            .select("summary_content") \
            .eq("user_id", str(user_id)) \
            .order("created_at", desc=True) \
            .limit(20) \
            .execute()
        # Kembalikan data jika ada, atau list kosong jika tidak
        return response.data if response and response.data else []
    except APIError as e:
        # Tangani error spesifik dari Supabase/PostgREST saat SELECT
        print(f"APIError getting conversation summaries: {e}")
        return [] # Kembalikan list kosong jika error
    except Exception as e:
        # Tangani error umum lainnya
        print(f"Unexpected error getting conversation summaries: {e}")
        return []

def get_messages_in_conversation(authed_client, conversation_id: UUID) -> List[dict]:
    """
    Mengambil semua pesan (riwayat chat) dalam satu conversation tertentu.
    Menggunakan klien Supabase yang sudah diautentikasi.
    """
    try:
        # Query tabel 'Messages'
        # PERIKSA: Menggunakan nama tabel "Messages" (M besar) sesuai SQL Anda
        response = authed_client.table("Messages") \
            .select("*") \
            .eq("conversation_id", str(conversation_id)) \
            .order("created_at", desc=False) \
            .execute()
        # Kembalikan data jika ada, atau list kosong jika tidak
        return response.data if response and response.data else []
    except APIError as e:
        # Tangani error spesifik dari Supabase/PostgREST saat SELECT
        print(f"APIError getting messages in conversation: {e}")
        # Jika error karena tabel tidak ada, beri pesan lebih jelas
        if e.code == '42P01': 
             # PERIKSA: Pastikan tabel 'Messages' benar-benar ada
             print("Pastikan tabel 'public.Messages' ada.")
        return [] # Kembalikan list kosong jika error
    except Exception as e:
        # Tangani error umum lainnya
        print(f"Unexpected error getting messages in conversation: {e}")
        return []

