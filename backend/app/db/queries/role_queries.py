from typing import Optional, List
from app.db.supabase_client import get_supabase_client

supabase = get_supabase_client()

# NOTE: Anda harus membuat RPC function 'find_most_relevant_role' di Supabase
def find_relevant_role(query_embedding: List[float]) -> Optional[dict]:
    try:
        response = supabase.rpc("find_most_relevant_role", {"query_embedding": query_embedding}).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error calling find_most_relevant_role RPC: {e}")
        return None