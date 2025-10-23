from typing import Dict, Optional, AsyncIterable # <-- Tambahkan AsyncIterable
from uuid import UUID
from app.core.config import settings
from app.services.embedding_service import generate_embedding
# PERUBAHAN: Impor fungsi streaming dari gemini_config
from app.services.gemini_config import stream_gemini_response 
from app.db.queries.role_queries import find_relevant_role 
from app.db.queries.conversation_queries import find_relevant_history
# from app.db.queries.canvas_queries import get_blocks_in_canvas # Mungkin tidak dipakai
from app.models.user import SubscriptionTier
from app.db.queries.prompt_queries import get_super_master_prompt

# PERUBAHAN: Fungsi ini sekarang mengembalikan AsyncIterable[str] dan metadata terpisah
async def run_agent_flow(
    authed_client, 
    user_id: Optional[UUID], 
    current_canvas_id: Optional[UUID], 
    user_message: str, 
    user_tier: SubscriptionTier
) -> tuple[AsyncIterable[str], Dict]: # <-- Mengembalikan stream dan dict metadata
    """
    Menjalankan alur logika utama agent AI, menghasilkan stream teks dan metadata.
    """
    query_embedding = await generate_embedding(user_message)
    if not query_embedding:
        # Untuk error sebelum stream, kita bisa raise exception atau return stream error
        async def error_stream():
            yield "Gagal menghasilkan embedding untuk pesan Anda."
        return error_stream(), {"role_used": "Error"} # Kembalikan stream error dan metadata error

    relevant_role = find_relevant_role(authed_client, query_embedding)
    
    role_name = "General Assistant" # Default
    master_prompt_child = "Kamu adalah asisten umum yang siap membantu berbagai tugas."

    # Periksa jika role ditemukan dan validasi tier
    if relevant_role:
        # Gunakan .get() dengan aman
        required_tier_str = relevant_role.get('required_tier', 'user') # Default ke 'user' jika tidak ada
        role_tier_valid = True
        if required_tier_str == 'pro' and user_tier != SubscriptionTier.pro and user_tier != SubscriptionTier.admin:
             role_tier_valid = False # Pengguna tidak memenuhi syarat

        if role_tier_valid:
            master_prompt_child = relevant_role.get('prompt_content', master_prompt_child)
            role_name = relevant_role.get('role_name', role_name)
        else:
             # Beri tahu pengguna jika role premium tidak bisa dipakai
             print(f"User tier ({user_tier.value}) insufficient for role '{relevant_role.get('role_name')}' (requires {required_tier_str}). Using default.")
             # Anda bisa juga menambahkan pesan ke stream jika mau
    else:
         print("Warning: find_relevant_role returned None. Using default role.")


    relevant_history = find_relevant_history(authed_client, query_embedding)
    formatted_history = "\n".join([f"Histori: {msg.get('role', 'unknown')} - {msg.get('content', '')}" for msg in relevant_history])

    # Asumsi get_super_master_prompt tidak perlu authed_client
    super_master_prompt = get_super_master_prompt() 

    final_prompt = f"""
{super_master_prompt}
--- MASTER PROMPT ANAK (PERAN) ---
{master_prompt_child}
--- END MASTER PROMPT ANAK ---
--- KONTeks MEMORI JANGKA PENDEK ---
{formatted_history}
--- END KONTeks MEMORI ---
--- PERMINTAAN PENGGUNA ---
{user_message}
--- END PERMINTAAN ---
"""
    # PERUBAHAN: Panggil fungsi streaming Gemini
    ai_response_stream = stream_gemini_response(final_prompt)
    
    # Kembalikan stream dan metadata
    return ai_response_stream, {"role_used": role_name}

