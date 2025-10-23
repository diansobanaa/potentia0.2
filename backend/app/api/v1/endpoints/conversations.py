from fastapi import APIRouter, Depends, HTTPException, Request, Body
# PERUBAHAN: Impor StreamingResponse
from fastapi.responses import StreamingResponse
# PERUBAHAN: Hapus GuestUser dari impor user, pindahkan ke impor dependencies
from typing import List, Union, AsyncIterable, Dict, Optional
from uuid import UUID

# Impor model yang diperlukan
from app.models.conversation import MessageCreate, Message
from app.models.user import User, SubscriptionTier 
# PERUBAHAN: Gunakan dependency yang tepat DAN impor GuestUser dari sini
from app.core.dependencies import get_canvas_access, GuestUser
from app.services.ai_agent_service import run_agent_flow
from app.services.rate_limit_service import check_guest_limit, check_user_limit
from app.services.embedding_service import generate_embedding
# PERUBAHAN: Pastikan semua fungsi query yang dibutuhkan diimpor
from app.db.queries.conversation_queries import get_or_create_conversation, add_message, get_messages_in_conversation
import asyncio # Untuk menangani stream
import json # Untuk mengirim metadata jika menggunakan SSE

router = APIRouter(
    prefix="/conversations",
    tags=["conversations"]
)

# PERUBAHAN: Endpoint ini sekarang mengembalikan StreamingResponse
@router.post("/{canvas_id}/send")
async def send_message_in_canvas(
    # --- Argumen Tanpa Default ---
    canvas_id: UUID,
    request: Request, # <-- DIPINDAHKAN KE SINI
    # --- Argumen Dengan Default ---
    # Pastikan MessageCreate memiliki field 'content'
    message_data: MessageCreate = Body(...),
    # Menggunakan get_canvas_access yang sudah mengembalikan dict berisi user, client, canvas
    access_info: dict = Depends(get_canvas_access),
) -> StreamingResponse:
    """
    Menerima pesan pengguna, memprosesnya melalui AI agent (run_agent_flow),
    dan mengembalikan respons AI secara streaming ke klien.
    Juga menyimpan pesan pengguna dan AI ke database.
    """
    # Ekstrak informasi yang dibutuhkan dari dependency
    authed_client = access_info["client"]
    current_user_or_guest = access_info["user"]
    # canvas = access_info["canvas"] # Ambil canvas jika perlu validasi lebih lanjut

    is_guest: bool
    user_id: Optional[UUID] = None
    user_tier: SubscriptionTier

    # Tentukan tipe pengguna dan periksa rate limit
    if isinstance(current_user_or_guest, GuestUser):
        is_guest = True
        user_tier = SubscriptionTier.user # Tier default untuk tamu
        client_ip = request.client.host if request.client else "unknown"
        # Cek rate limit untuk tamu
        if not check_guest_limit(authed_client, client_ip): # Teruskan authed_client jika perlu
            raise HTTPException(status_code=429, detail="Guest message limit reached.")
    elif isinstance(current_user_or_guest, User):
        is_guest = False
        user_id = current_user_or_guest.id
        user_tier = current_user_or_guest.subscription_tier
        # Cek rate limit untuk pengguna terdaftar
        if not check_user_limit(authed_client, user_id, user_tier.value): # Teruskan authed_client jika perlu
             raise HTTPException(status_code=429, detail="User message limit reached.")
    else:
        # Jika tipe pengguna tidak dikenali (seharusnya tidak terjadi)
        raise HTTPException(status_code=500, detail="Unknown user type")

    # --- LANGKAH SEBELUM STREAMING ---
    # 1. Dapatkan atau buat ID conversation terlebih dahulu
    conversation_result = get_or_create_conversation(authed_client, canvas_id, user_id)
    if not conversation_result:
         # Jika gagal mendapatkan/membuat conversation, hentikan proses
         raise HTTPException(status_code=500, detail="Could not get or create conversation.")
    # Asumsi nama kolom primary key adalah 'conversation_id'
    conversation_id = conversation_result["conversation_id"]

    # 2. Simpan pesan PENGGUNA ke database SEBELUM memulai stream AI
    user_embedding = await generate_embedding(message_data.content)
    if user_embedding:
        # Panggil add_message dengan authed_client
        add_message(authed_client, conversation_id, "user", message_data.content, user_embedding)
    else:
        # Beri peringatan jika embedding gagal, tapi mungkin tetap lanjutkan?
        print(f"Warning: Could not generate embedding for user message in conv {conversation_id}")
        # Pertimbangkan apakah akan menyimpan pesan tanpa embedding atau tidak
        # add_message(authed_client, conversation_id, "user", message_data.content, None)

    # --- PERSIAPAN STREAMING ---
    # Definisikan generator asinkron yang akan menghasilkan potongan teks
    async def stream_generator() -> AsyncIterable[str]:
        full_ai_response = "" # Variabel untuk mengumpulkan seluruh respons AI
        metadata = {} # Variabel untuk menyimpan metadata dari agent
        try:
            # Panggil agent flow yang sekarang mengembalikan stream dan metadata
            ai_stream, agent_metadata = await run_agent_flow(
                authed_client=authed_client, # Teruskan client yang sudah diautentikasi
                user_id=user_id,
                current_canvas_id=canvas_id,
                user_message=message_data.content,
                user_tier=user_tier
            )
            # Simpan metadata yang dikembalikan oleh agent
            metadata.update(agent_metadata)

            # Iterasi melalui stream AI yang dihasilkan oleh run_agent_flow
            async for chunk in ai_stream:
                yield chunk # Kirim potongan teks ke klien (frontend)
                full_ai_response += chunk # Kumpulkan potongan teks

            # --- STREAMING SELESAI ---
            # Proses ini berjalan SETELAH semua potongan teks dikirim ke klien

            # 4. Simpan pesan AI LENGKAP ke database SETELAH streaming selesai
            # Hanya simpan jika respons tidak kosong dan tidak berisi pesan error internal
            if full_ai_response and "Maaf, terjadi error" not in full_ai_response and "Gagal menghasilkan embedding" not in full_ai_response:
                 ai_embedding = await generate_embedding(full_ai_response)
                 if ai_embedding:
                     # Panggil add_message dengan authed_client
                     add_message(authed_client, conversation_id, "ai", full_ai_response, ai_embedding)
                 else:
                     # Beri peringatan jika embedding gagal
                     print(f"Warning: Could not generate embedding for AI response in conv {conversation_id}")
                     # Pertimbangkan menyimpan tanpa embedding
                     # add_message(authed_client, conversation_id, "ai", full_ai_response, None)
            else:
                 # Jangan simpan jika respons AI kosong atau error
                 print(f"AI response was empty or contained error, not saving to DB. Full response: '{full_ai_response}'")

            # (Opsional) Mengirim metadata atau sinyal akhir stream jika menggunakan Server-Sent Events (SSE)
            # Format SSE: event: <nama_event>\ndata: <data_json>\n\n
            # yield f"event: metadata\ndata: {json.dumps(metadata)}\n\n"
            # yield f"event: end\ndata: Stream finished\n\n"

        except Exception as e:
            # Tangani error yang mungkin terjadi selama proses streaming atau penyimpanan
            print(f"Error during streaming or post-stream processing: {e}")
            # Kirim pesan error sebagai bagian dari stream ke klien
            yield f"Terjadi kesalahan internal saat memproses respons AI: {str(e)}"
            # Pertimbangkan log error yang lebih detail atau mekanisme notifikasi

    # 5. Kembalikan StreamingResponse
    # media_type='text/plain' cocok untuk stream teks sederhana.
    # Gunakan 'text/event-stream' jika Anda memformat output sebagai Server-Sent Events (SSE) di dalam generator.
    return StreamingResponse(stream_generator(), media_type="text/plain")


# Endpoint untuk mengambil riwayat chat (tidak diubah menjadi streaming)
@router.get("/{canvas_id}/history", response_model=List[Message]) # Pastikan model Message diimpor dan benar
async def get_chat_history(
    canvas_id: UUID,
    # Menggunakan dependency yang sama untuk mendapatkan user dan client terotentikasi
    access_info: dict = Depends(get_canvas_access)
):
    """Mengambil riwayat pesan (non-streaming) dari sebuah canvas."""
    authed_client = access_info["client"]
    current_user_or_guest = access_info["user"]

    user_id: Optional[UUID] = None
    # Dapatkan user_id jika pengguna bukan guest
    if isinstance(current_user_or_guest, User):
        user_id = current_user_or_guest.id

    # Ambil ID conversation terlebih dahulu menggunakan client terotentikasi
    conversation = get_or_create_conversation(authed_client, canvas_id, user_id)
    if not conversation:
        # Jika tidak ada conversation (misal, belum pernah chat), kembalikan daftar kosong
        return []

    # Asumsi nama kolom primary key adalah 'conversation_id'
    conversation_id = conversation["conversation_id"]

    # Ambil pesan dari conversation menggunakan client terotentikasi
    messages = get_messages_in_conversation(authed_client, conversation_id)
    # Kembalikan daftar pesan
    return messages

