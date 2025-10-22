from typing import List, Dict, Optional
from uuid import UUID
from app.core.config import settings
from app.services.embedding_service import generate_embedding
from app.services.gemini_config import call_gemini_api
from app.db.queries.role_queries import find_relevant_role
from app.db.queries.conversation_queries import find_relevant_history
from app.db.queries.canvas_queries import get_blocks_in_canvas
from app.models.user import SubscriptionTier
from app.db.queries.prompt_queries import get_super_master_prompt

async def run_agent_flow(
    user_id: Optional[UUID], 
    current_canvas_id: Optional[UUID], 
    user_message: str, 
    user_tier: SubscriptionTier
) -> Dict:
    query_embedding = await generate_embedding(user_message)
    if not query_embedding:
        return {"status": "error", "message": "Failed to generate embedding."}
    
    relevant_role = find_relevant_role(query_embedding)
    if not relevant_role or (user_tier == SubscriptionTier.user and relevant_role['required_tier'] == 'pro'):
        master_prompt_child = "Kamu adalah asisten umum yang siap membantu berbagai tugas."
        role_name = "General Assistant"
    else:
        master_prompt_child = relevant_role['prompt_content']
        role_name = relevant_role['role_name']

    relevant_history = find_relevant_history(query_embedding)
    formatted_history = "\n".join([f"Histori: {msg['role']} - {msg['content']}" for msg in relevant_history])

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
    ai_response_text = await call_gemini_api(final_prompt)
    if not ai_response_text or "error" in ai_response_text.lower():
        return {"status": "error", "message": "Failed to get response from AI."}

    return {"status": "success", "response": ai_response_text, "metadata": {"role_used": role_name}}