from typing import List, Optional
from uuid import UUID
from app.db.supabase_client import get_supabase_client

supabase = get_supabase_client()

def get_or_create_conversation(canvas_id: Optional[UUID], user_id: Optional[UUID]) -> dict:
    query = supabase.table("Conversations").select("*").eq("canvas_id", str(canvas_id))
    if user_id:
        query = query.eq("user_id", str(user_id))
    else:
        query = query.is_("user_id", "null")
        
    response = query.maybe_single().execute()
    if response.data:
        return response.data
    
    new_conv_payload = {"canvas_id": str(canvas_id)}
    if user_id:
        new_conv_payload["user_id"] = str(user_id)
        
    new_conv_response = supabase.table("Conversations").insert(new_conv_payload).execute()
    return new_conv_response.data[0]

def find_relevant_history(query_embedding: List[float]) -> List[dict]:
    try:
        response = supabase.rpc("find_relevant_conversation_history", {"query_embedding": query_embedding}).execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"Error calling find_relevant_conversation_history RPC: {e}")
        return []

def add_message(conversation_id: UUID, role: str, content: str, embedding: List[float]) -> Optional[dict]:
    """
    Menyimpan pesan dan embedding yang sudah disiapkan ke database.
    """
    response = supabase.table("Messages").insert({
        "conversation_id": str(conversation_id), 
        "role": role, 
        "content": content, 
        "vector_embedding": embedding
    }).execute()
    return response.data[0] if response.data else None

def claim_guest_session(conversation_id: UUID, user_id: UUID) -> bool:
    response = supabase.table("Conversations").update({"user_id": str(user_id)}).eq("conversation_id", str(conversation_id)).execute()
    return len(response.data) > 0

def get_all_conversation_summaries(user_id: UUID) -> List[dict]:
    """
    Mengambil semua ringkasan percakapan dari user untuk konteks global.
    """
    supabase = get_supabase_client()
    response = supabase.table("ConversationSummaries") \
        .select("summary_content") \
        .eq("user_id", str(user_id)) \
        .order("created_at", desc=True) \
        .limit(20) \
        .execute()
    return response.data if response.data else []