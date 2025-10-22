from typing import List, Optional
from uuid import UUID
from app.db.supabase_client import get_supabase_client

supabase = get_supabase_client()

def create_block(canvas_id: UUID, block_data: dict) -> Optional[dict]:
    response = supabase.table("Blocks").insert({**block_data, "canvas_id": str(canvas_id)}).execute()
    return response.data[0] if response.data else None

def get_blocks_in_canvas(canvas_id: UUID) -> List[dict]:
    response = supabase.table("Blocks").select("*").eq("canvas_id", str(canvas_id)).order("y_order").execute()
    return response.data if response.data else None

def update_block(block_id: UUID, update_data: dict) -> Optional[dict]:
    response = supabase.table("Blocks").update(update_data).eq("block_id", str(block_id)).execute()
    return response.data[0] if response.data else None

def delete_block(block_id: UUID) -> bool:
    response = supabase.table("Blocks").delete().eq("block_id", str(block_id)).execute()
    return len(response.data) > 0